"""导出产物列表。只读 export_artifact, 文件格式复用 ledger targets。"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.db.schema import Approval, ExportArtifact, Store, Voucher
from crosserp.iam.scope import legal_entity_contains, store_contains
from crosserp.ledger.write_service import export_target_catalog
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal

_CATALOG = export_target_catalog()
_TARGET_IDS = frozenset(target_id for target_id, _types in _CATALOG)
_AFFILIATED_TYPES = frozenset(supported for _target_id, types in _CATALOG for supported in types)
_SORT_FIELDS = frozenset({"createdAt", "target", "fileName"})


def list_exports(
    session: Session,
    *,
    principal: Principal,
    permission_service: PermissionService,
    page: int,
    page_size: int,
    q: str | None,
    sort: str,
) -> dict[str, Any]:
    descending = sort.startswith("-")
    field = sort[1:] if descending else sort
    if field not in _SORT_FIELDS:
        raise APIError(ErrorCode.VALIDATION_FAILED, "sort 只支持 createdAt、target 或 fileName")
    rows = list(
        session.execute(
            select(ExportArtifact, Approval)
            .join(Approval, Approval.id == ExportArtifact.approval_id)
            .where(ExportArtifact.target_id.in_(_TARGET_IDS))
        ).all()
    )
    visible = [pair for pair in rows if _in_scope(session, pair[1], principal, permission_service)]
    if q:
        needle = q.casefold()
        visible = [pair for pair in visible if _matches(pair[0], needle)]
    visible.sort(key=lambda pair: _sort_key(pair[0], field), reverse=descending)
    total = len(visible)
    start = (page - 1) * page_size
    page_rows = visible[start : start + page_size]
    return {
        "items": [_item(artifact) for artifact, _approval in page_rows],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


def _item(artifact: ExportArtifact) -> dict[str, Any]:
    return {
        "exportId": str(artifact.id),
        "target": artifact.target_id,
        "fileName": _file_name(artifact),
        "sha256": artifact.sha256,
        "approvalId": str(artifact.approval_id),
        "createdAt": artifact.created_at.isoformat(),
    }


def _file_name(artifact: ExportArtifact) -> str | None:
    if artifact.file_path is None:
        return None
    return Path(artifact.file_path).name


def _matches(artifact: ExportArtifact, needle: str) -> bool:
    parts = [artifact.target_id, artifact.sha256, str(artifact.approval_id)]
    file_name = _file_name(artifact)
    if file_name is not None:
        parts.append(file_name)
    return any(needle in part.casefold() for part in parts)


def _sort_key(artifact: ExportArtifact, field: str) -> tuple[int, str, str]:
    if field == "createdAt":
        value = artifact.created_at.isoformat()
        missing = 0
    elif field == "target":
        value = artifact.target_id.casefold()
        missing = 0
    else:
        file_name = _file_name(artifact)
        if file_name is None:
            value = ""
            missing = 1
        else:
            value = file_name.casefold()
            missing = 0
    return (missing, value, str(artifact.id))


def _in_scope(
    session: Session,
    approval: Approval,
    principal: Principal,
    permission_service: PermissionService,
) -> bool:
    store_id, legal_entity, claimed = _affiliation(session, approval)
    if not claimed:
        return True
    stores = permission_service.store_scope(principal, "ExportPackage")
    books = permission_service.legal_entity_scope(principal, "ExportPackage")
    if store_id is None or not store_contains(stores, store_id):
        return False
    return legal_entity_contains(books, legal_entity)


def _affiliation(session: Session, approval: Approval) -> tuple[UUID | None, str | None, bool]:
    if approval.target_type not in _AFFILIATED_TYPES:
        return None, None, False
    if approval.target_type == "voucher":
        voucher = session.get(Voucher, UUID(approval.target_id))
        if voucher is None:
            return None, None, True
        store = session.get(Store, voucher.store_id)
        if store is None:
            return voucher.store_id, None, True
        return store.id, store.legal_entity, True
    store_name, separator, period = approval.target_id.rpartition(":")
    if not separator or not store_name or len(period) != 7:
        return None, None, True
    store = session.scalar(select(Store).where(Store.name == store_name))
    if store is None:
        return None, None, True
    return store.id, store.legal_entity, True


__all__ = ["list_exports"]
