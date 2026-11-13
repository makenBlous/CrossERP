"""按实体版本前快照回退目录实体。新建动作的反向停用也在这里执行。"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.catalog.bundles import bundle_in_store_scope, deactivate_bundle
from crosserp.catalog.sku import ensure_store_allowed
from crosserp.db.schema import (
    Brand,
    Bundle,
    Category,
    CleansingIssue,
    DedupCandidate,
    ImportBatch,
    Issue,
    Listing,
    Match,
    ReconRun,
    Sku,
    SkuMapping,
    Store,
)
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal

UNDO_UNSUPPORTED = "该实体不支持撤销"
EMPTY_BEFORE = "撤销前快照没有可回退字段"


class CatalogUndoRestore:
    """目录实体的字段回退与新建反向动作。"""

    def supports(self, entity_type: str) -> bool:
        return entity_type in _MODEL or entity_type in _CUSTOM

    def restorable_fields(self, entity_type: str) -> frozenset[str]:
        if entity_type in _CUSTOM:
            return frozenset({"status", "resolutionNote"})
        if entity_type not in _RESTORABLE:
            raise APIError(ErrorCode.VALIDATION_FAILED, UNDO_UNSUPPORTED)
        return _RESTORABLE[entity_type]

    def restore(
        self, session: Session, entity_type: str, entity_id: str, before: dict[str, Any]
    ) -> None:
        if not self.supports(entity_type):
            raise APIError(ErrorCode.VALIDATION_FAILED, UNDO_UNSUPPORTED)
        if entity_type in _CUSTOM:
            _CUSTOM[entity_type](session, entity_id, before)
            return
        present = [name for name in self.restorable_fields(entity_type) if name in before]
        if not present:
            raise APIError(ErrorCode.VALIDATION_FAILED, EMPTY_BEFORE)
        model = _MODEL[entity_type]
        row: Any = session.get(model, UUID(entity_id))
        if row is None:
            raise APIError(ErrorCode.NOT_FOUND, "撤销目标不存在")
        _FIELDS[entity_type](row, before)
        row.updated_at = datetime.now(UTC)
        if entity_type != "Sku":
            row.version = int(row.version) + 1
        session.flush()

    def apply_reverse(
        self,
        session: Session,
        *,
        action: str,
        entity_id: str,
        payload: dict[str, Any],
        principal: Principal,
        permission_service: PermissionService,
    ) -> dict[str, Any]:
        if action not in _REVERSE:
            raise APIError(ErrorCode.VALIDATION_FAILED, "撤销反向动作未注册")
        return _REVERSE[action](session, entity_id, payload, principal, permission_service)


def supports_undo(entity_type: str) -> bool:
    return CATALOG_UNDO_RESTORE.supports(entity_type)


def restore_entity(
    session: Session, entity_type: str, entity_id: str, before: dict[str, Any]
) -> None:
    CATALOG_UNDO_RESTORE.restore(session, entity_type, entity_id, before)


def _text(row: Any, before: dict[str, Any], *names: str) -> None:
    for name in names:
        if name in before:
            setattr(row, _snake(name), before[name])


def _store(row: Store, before: dict[str, Any]) -> None:
    _text(row, before, "name", "platform", "marketplace", "currency", "legalEntity")


def _brand(row: Brand, before: dict[str, Any]) -> None:
    _text(row, before, "name", "active")


def _category(row: Category, before: dict[str, Any]) -> None:
    _text(row, before, "name", "active")


def _listing(row: Listing, before: dict[str, Any]) -> None:
    _text(row, before, "status", "asin")


def _sku(row: Sku, before: dict[str, Any]) -> None:
    _text(row, before, "title", "active")


def _mapping(row: SkuMapping, before: dict[str, Any]) -> None:
    _text(row, before, "state", "internalSku")


def _cleansing_issue(row: CleansingIssue, before: dict[str, Any]) -> None:
    if "status" in before:
        row.status = str(before["status"])
    if "handler" in before:
        row.handler = before["handler"]
    if "version" in before:
        row.version = int(before["version"])


def _dedup_candidate(row: DedupCandidate, before: dict[str, Any]) -> None:
    if "status" in before:
        row.status = str(before["status"])
    if "version" in before:
        row.version = int(before["version"])


def _ingest_batch(row: ImportBatch, before: dict[str, Any]) -> None:
    if "status" in before:
        row.status = str(before["status"])
    if "projectedCount" in before:
        row.projected_count = int(before["projectedCount"])
    if "counts" in before:
        row.counts_json = before["counts"]
    if "version" in before:
        row.version = int(before["version"])


def _bundle(row: Bundle, before: dict[str, Any]) -> None:
    if "bundleSku" in before:
        row.bundle_sku = before["bundleSku"]
    if "components" in before:
        row.components_json = before["components"]
    if "active" in before:
        row.active = before["active"]


def _snake(name: str) -> str:
    names = {
        "internalSku": "internal_sku",
        "bundleSku": "bundle_sku",
        "legalEntity": "legal_entity",
    }
    if name in names:
        return names[name]
    return name


def _touch(row: Any, *, bump_version: bool) -> None:
    row.updated_at = datetime.now(UTC)
    if bump_version:
        row.version = int(row.version) + 1


def _load(session: Session, model: type[Any], entity_id: str) -> Any:
    row = session.get(model, UUID(entity_id))
    if row is None:
        raise APIError(ErrorCode.NOT_FOUND, "撤销目标不存在")
    return row


def _require_key(payload: dict[str, Any], key: str, action: str) -> Any:
    if key not in payload:
        raise APIError(ErrorCode.VALIDATION_FAILED, f"{action} 撤销缺少 {key}")
    return payload[key]


def _reverse_brand_status(
    session: Session,
    entity_id: str,
    payload: dict[str, Any],
    _principal: Principal,
    _permission_service: PermissionService,
) -> dict[str, Any]:
    row = _load(session, Brand, entity_id)
    active = bool(_require_key(payload, "active", "Brand.status"))
    previous = bool(row.active)
    row.active = active
    _touch(row, bump_version=True)
    session.flush()
    return {"before": {"active": previous}, "after": {"active": row.active}}


def _reverse_sku_update(
    session: Session,
    entity_id: str,
    payload: dict[str, Any],
    principal: Principal,
    permission_service: PermissionService,
) -> dict[str, Any]:
    row = _load(session, Sku, entity_id)
    ensure_store_allowed(principal, row.store_id, permission_service)
    active = bool(_require_key(payload, "active", "Sku.update"))
    previous = bool(row.active)
    row.active = active
    _touch(row, bump_version=False)
    session.flush()
    return {"before": {"active": previous}, "after": {"active": row.active}}


def _reverse_bundle_deactivate(
    session: Session,
    entity_id: str,
    _payload: dict[str, Any],
    principal: Principal,
    permission_service: PermissionService,
) -> dict[str, Any]:
    row = _load(session, Bundle, entity_id)
    if not bundle_in_store_scope(session, row, principal, permission_service):
        raise not_found(message="组合装不存在")
    if not row.active:
        raise APIError(ErrorCode.ILLEGAL_TRANSITION, "组合装已作废")
    before, after = deactivate_bundle(session, row)
    return {"before": before, "after": after}


def _reverse_listing_status(
    session: Session,
    entity_id: str,
    payload: dict[str, Any],
    _principal: Principal,
    _permission_service: PermissionService,
) -> dict[str, Any]:
    row = _load(session, Listing, entity_id)
    status = str(_require_key(payload, "status", "Listing.status"))
    previous = row.status
    row.status = status
    _touch(row, bump_version=True)
    session.flush()
    return {"before": {"status": previous}, "after": {"status": row.status}}


def _reverse_category_status(
    session: Session,
    entity_id: str,
    payload: dict[str, Any],
    _principal: Principal,
    _permission_service: PermissionService,
) -> dict[str, Any]:
    row = _load(session, Category, entity_id)
    status = str(_require_key(payload, "status", "Category.status"))
    previous = bool(row.active)
    row.active = status == "active"
    _touch(row, bump_version=True)
    session.flush()
    return {"before": {"active": previous}, "after": {"active": row.active}}


def _reverse_mapping_delete(
    session: Session,
    entity_id: str,
    _payload: dict[str, Any],
    _principal: Principal,
    _permission_service: PermissionService,
) -> dict[str, Any]:
    row = _load(session, SkuMapping, entity_id)
    previous = row.state
    if previous == "rejected":
        raise APIError(ErrorCode.ILLEGAL_TRANSITION, "映射已停用")
    row.state = "rejected"
    _touch(row, bump_version=True)
    session.flush()
    return {"before": {"state": previous}, "after": {"state": row.state}}


def _recon_run(session: Session, entity_id: str, before: dict[str, Any]) -> None:
    """创建对账运行的撤销删除该运行。有前快照时只回写状态。"""
    row = session.get(ReconRun, UUID(entity_id))
    if row is None:
        raise APIError(ErrorCode.NOT_FOUND, "撤销目标不存在")
    if not before:
        session.execute(delete(Match).where(Match.recon_run_id == row.id))
        session.execute(delete(Issue).where(Issue.recon_run_id == row.id))
        session.delete(row)
        session.flush()
        return
    if "status" in before:
        row.status = str(before["status"])
    session.flush()


def _recon_issue(session: Session, entity_id: str, before: dict[str, Any]) -> None:
    row = session.get(Issue, UUID(entity_id))
    if row is None:
        raise APIError(ErrorCode.NOT_FOUND, "撤销目标不存在")
    if "status" in before:
        row.status = str(before["status"])
    if "resolutionNote" in before:
        note = before["resolutionNote"]
        row.resolution_note = None if note is None else str(note)
    session.flush()


_CUSTOM: dict[str, Callable[[Session, str, dict[str, Any]], None]] = {
    "ReconRun": _recon_run,
    "ReconIssue": _recon_issue,
}
_MODEL = {
    "Brand": Brand,
    "Category": Category,
    "Listing": Listing,
    "Sku": Sku,
    "SkuMapping": SkuMapping,
    "Bundle": Bundle,
    "Store": Store,
    "IngestBatch": ImportBatch,
    "DedupCandidate": DedupCandidate,
    "CleansingIssue": CleansingIssue,
}
_FIELDS: dict[str, Callable[[Any, dict[str, Any]], None]] = {
    "Store": _store,
    "Brand": _brand,
    "Category": _category,
    "Listing": _listing,
    "Sku": _sku,
    "SkuMapping": _mapping,
    "Bundle": _bundle,
    "IngestBatch": _ingest_batch,
    "DedupCandidate": _dedup_candidate,
    "CleansingIssue": _cleansing_issue,
}
_RESTORABLE = {
    "Store": frozenset({"name", "platform", "marketplace", "currency", "legalEntity"}),
    "Brand": frozenset({"name", "active"}),
    "Category": frozenset({"name", "active"}),
    "Listing": frozenset({"status", "asin"}),
    "Sku": frozenset({"title", "active"}),
    "SkuMapping": frozenset({"state", "internalSku"}),
    "Bundle": frozenset({"bundleSku", "components", "active"}),
    "IngestBatch": frozenset({"status", "projectedCount", "counts", "version"}),
    "DedupCandidate": frozenset({"status", "version"}),
    "CleansingIssue": frozenset({"status", "handler", "version"}),
}
_REVERSE = {
    "Brand.status": _reverse_brand_status,
    "Sku.update": _reverse_sku_update,
    "Bundle.deactivate": _reverse_bundle_deactivate,
    "Listing.status": _reverse_listing_status,
    "Category.status": _reverse_category_status,
    "SkuMapping.delete": _reverse_mapping_delete,
}
CATALOG_UNDO_RESTORE = CatalogUndoRestore()
