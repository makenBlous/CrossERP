"""疑似重复实体的确定性合并服务。"""

# ruff: noqa: RUF001

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.db.schema import DedupCandidate, DocumentLink, EntityVersion, Sku
from crosserp.platform.audit import DefaultAuditRecorder
from crosserp.platform.principal import Principal

MergeHandler = Callable[[Session, DedupCandidate, list[str], str, Principal], dict[str, Any]]
_HANDLERS: dict[str, MergeHandler] = {}


def register_merge_handler(entity_type: str, handler: MergeHandler) -> None:
    """登记后续实体类型的合并实现。"""
    _HANDLERS[entity_type] = handler


def merge_candidate(
    session: Session,
    candidate: DedupCandidate,
    *,
    target_id: str | None,
    expected_version: int | None,
    principal: Principal,
) -> dict[str, Any]:
    if expected_version is not None and candidate.version != expected_version:
        raise APIError(
            ErrorCode.CONFLICT_VERSION,
            "疑似重复候选版本已变化",
            details={"expectedVersion": expected_version, "actualVersion": candidate.version},
        )
    if candidate.status != "open":
        raise APIError(ErrorCode.ILLEGAL_TRANSITION, "疑似重复候选已处理")
    ids = candidate_ids(candidate.ids)
    canonical_id = target_id or ids[0]
    if canonical_id not in ids:
        raise APIError(ErrorCode.VALIDATION_FAILED, "targetId 必须属于候选实体")
    handler = _HANDLERS.get(candidate.entity_type)
    if handler is None:
        raise not_found(message="该实体类型尚未注册合并处理器")
    result = handler(session, candidate, ids, canonical_id, principal)
    now = datetime.now(UTC)
    candidate.status = "merged"
    candidate.merged_target_id = canonical_id
    candidate.updated_at = now
    candidate.version += 1
    result.update(
        {
            "candidateId": str(candidate.id),
            "entityType": candidate.entity_type,
            "version": candidate.version,
        }
    )
    return result


def candidate_ids(value: Any) -> list[str]:
    if not isinstance(value, list) or len(value) < 2:
        raise APIError(ErrorCode.VALIDATION_FAILED, "候选 ids 至少需要两个实体")
    ids: list[str] = []
    for raw in value:
        try:
            parsed = str(UUID(str(raw)))
        except (TypeError, ValueError) as exc:
            raise APIError(ErrorCode.VALIDATION_FAILED, "候选 ids 必须是 UUID") from exc
        if parsed not in ids:
            ids.append(parsed)
    if len(ids) < 2:
        raise APIError(ErrorCode.VALIDATION_FAILED, "候选 ids 至少需要两个不同实体")
    return ids


def _stable_union(values: Iterable[Any]) -> list[Any]:
    unique: dict[str, Any] = {}
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        unique[key] = value
    return [unique[key] for key in sorted(unique)]


def _sku_merge(
    session: Session,
    candidate: DedupCandidate,
    ids: list[str],
    canonical_id: str,
    principal: Principal,
) -> dict[str, Any]:
    rows = {
        str(row.id): row
        for row in session.scalars(select(Sku).where(Sku.id.in_([UUID(value) for value in ids])))
    }
    if set(rows) != set(ids):
        raise not_found(message="SKU 实体不存在")
    canonical = rows[canonical_id]
    duplicates = [rows[value] for value in ids if value != canonical_id]
    for duplicate in duplicates:
        if duplicate.internal_sku != canonical.internal_sku:
            raise APIError(ErrorCode.VALIDATION_FAILED, "SKU 内部编码冲突，不能自动合并")

    old_aliases = list(canonical.aliases_json)
    old_sources = list(canonical.source_refs_json)
    aliases = _stable_union(
        [*old_aliases, canonical.platform_sku]
        + [value for row in duplicates for value in row.aliases_json]
        + [row.platform_sku for row in duplicates]
    )
    sources = _stable_union(
        [*old_sources] + [value for row in duplicates for value in row.source_refs_json]
    )
    preimage = {
        "canonical": {
            "id": canonical_id,
            "aliases": old_aliases,
            "sourceRefs": old_sources,
            "active": canonical.active,
        },
        "duplicates": [
            {"id": str(row.id), "active": row.active, "mergedIntoId": row.merged_into_id}
            for row in duplicates
        ],
    }
    canonical.aliases_json = aliases
    canonical.source_refs_json = sources
    for duplicate in duplicates:
        duplicate.active = False
        duplicate.merged_into_id = canonical_id

    duplicate_ids = {str(row.id) for row in duplicates}
    links = list(
        session.scalars(
            select(DocumentLink).where(
                DocumentLink.to_type == "Sku", DocumentLink.to_id.in_(duplicate_ids)
            )
        )
    )
    for link in links:
        existing = session.scalar(
            select(DocumentLink).where(
                DocumentLink.from_type == link.from_type,
                DocumentLink.from_id == link.from_id,
                DocumentLink.to_type == "Sku",
                DocumentLink.to_id == canonical_id,
                DocumentLink.relation == link.relation,
                DocumentLink.id != link.id,
            )
        )
        if existing is None:
            link.to_id = canonical_id
        else:
            session.delete(link)

    current_sku_version = session.scalar(
        select(func.max(EntityVersion.version)).where(
            EntityVersion.entity_type == "Sku", EntityVersion.entity_id == canonical_id
        )
    )
    sku_version = 0 if current_sku_version is None else int(current_sku_version)
    audit = DefaultAuditRecorder(session).record(
        principal=principal,
        entity="Sku",
        action="DedupCandidate.merge",
        diff={"before": preimage, "after": {"aliases": aliases, "sourceRefs": sources}},
    )
    session.add(
        EntityVersion(
            entity_type="Sku",
            entity_id=canonical_id,
            version=sku_version + 1,
            changed_at=datetime.now(UTC),
            actor_type="agent" if principal.is_agent else "human",
            actor_id=principal.user_id,
            on_behalf_of=principal.on_behalf_of,
            delegation_id=principal.delegation_id,
            run_id=principal.run_id,
            is_subagent=principal.is_subagent,
            channel=principal.channel,
            action_id="DedupCandidate.merge",
            before_json=preimage,
            after_json={"aliases": aliases, "sourceRefs": sources, "mergedIds": ids},
            diff_json={"before": preimage, "after": {"aliases": aliases, "sourceRefs": sources}},
            audit_log_id=audit.id,
        )
    )
    session.flush()
    expires = datetime.now(UTC) + timedelta(hours=24)
    return {
        "canonicalId": canonical_id,
        "mergedIds": ids,
        "aliases": aliases,
        "sourceRefs": sources,
        "undo": {"preimage": preimage, "expiresAt": expires.isoformat()},
    }


register_merge_handler("Sku", _sku_merge)

__all__ = ["candidate_ids", "merge_candidate", "register_merge_handler"]
