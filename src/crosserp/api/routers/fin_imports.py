"""财务导入批次 JSON API。"""

# FastAPI 依赖声明需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _page, _principal_db, _require, _write_guard
from crosserp.api.schemas import PageParams
from crosserp.catalog.undo_restore import CATALOG_UNDO_RESTORE
from crosserp.connectors.importer import import_file
from crosserp.connectors.registry import detect
from crosserp.core.errors import DuplicateImportError
from crosserp.db.schema import ActionExecution, ImportBatch, OrderLine, Settlement
from crosserp.iam.scope import AllStores, StoreScope
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.idempotency import caller_scope, current_http_scope
from crosserp.platform.permissions import PermissionService, get_permission_service
from crosserp.platform.principal import Principal

router = APIRouter()

_SORT_FIELDS = {
    "createdAt": (ImportBatch.imported_at, ImportBatch.id, False, False),
    "-createdAt": (ImportBatch.imported_at, ImportBatch.id, True, False),
    "status": (ImportBatch.status, ImportBatch.id, False, True),
    "-status": (ImportBatch.status, ImportBatch.id, True, True),
}


def _batch_store_ids(session: Session, batch_id: UUID) -> set[UUID]:
    """从 Settlement 和 OrderLine 收集批次关联的店铺 id。"""
    store_ids: set[UUID] = set()
    store_ids.update(
        session.scalars(select(Settlement.store_id).where(Settlement.source_batch_id == batch_id))
    )
    store_ids.update(
        session.scalars(select(OrderLine.store_id).where(OrderLine.source_batch_id == batch_id))
    )
    return store_ids


def _batch_in_scope(session: Session, batch_id: UUID, scope: StoreScope) -> bool:
    """批次是否落在店铺范围内。"""
    if isinstance(scope, AllStores):
        return True
    store_ids = _batch_store_ids(session, batch_id)
    return bool(store_ids & scope)


def _filter_batches_in_scope(
    session: Session, batches: list[ImportBatch], scope: StoreScope
) -> list[ImportBatch]:
    if isinstance(scope, AllStores):
        return batches
    return [b for b in batches if _batch_in_scope(session, b.id, scope)]


def _reject_other_identity_key(session: Session, principal: Principal, key: str | None) -> None:
    """他人已占用的幂等键不可见: 返回 404 且不另建批次."""
    if not key:
        return
    identity = caller_scope(principal)
    http = current_http_scope("IngestBatch.create")
    foreign = session.scalar(
        select(ActionExecution.id).where(
            ActionExecution.idempotency_key == key,
            ActionExecution.http_method == http.method,
            ActionExecution.route_template == http.route_template,
            ActionExecution.caller_identity != identity.caller_identity,
        )
    )
    if foreign is not None:
        raise not_found()


def _batch_payload(row: ImportBatch) -> dict[str, Any]:
    counts = {
        "landed": row.landed_count,
        "valid": row.valid_count,
        "duplicate": row.duplicate_count,
        "quarantined": row.quarantined_count,
        "projected": row.projected_count,
    }
    return {
        "id": str(row.id),
        "source": row.source,
        "kind": row.kind,
        "status": row.status,
        "fileSha256": row.file_sha256,
        "mappingRuleVersion": row.mapping_rule_version,
        "counts": counts,
        "supersedes": str(row.supersedes_id) if row.supersedes_id else None,
        "createdBy": str(row.created_by) if row.created_by else None,
        "onBehalfOf": str(row.on_behalf_of) if row.on_behalf_of else None,
        "createdAt": (row.received_at or row.imported_at).isoformat(),
        "version": row.version,
    }


class _FileMetaForm:
    def __init__(self, meta: str | None = None) -> None:
        self.meta = meta

    @classmethod
    def as_form(cls, meta: Annotated[str | None, Form()] = None) -> _FileMetaForm:
        return cls(meta=meta)


@router.get("/finance/imports")
@api_endpoint(
    entity="IngestBatch",
    action="IngestBatch.list",
    permission="integration:read",
    risk_tier="none",
    idempotency="none",
)
def list_imports(
    request: Request,
    params: PageParams = Depends(),
    q: str | None = Query(None),
    sort: str = Query("-createdAt"),
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _require(request, principal, "integration:read", entity="IngestBatch")
        scope = permission_service.store_scope(principal, "IngestBatch")
        if sort not in _SORT_FIELDS:
            raise APIError(ErrorCode.VALIDATION_ERROR, "sort 参数无效")
        col_primary, col_secondary, desc_primary, desc_secondary = _SORT_FIELDS[sort]
        statement = select(ImportBatch).order_by(
            col_primary.desc() if desc_primary else col_primary.asc(),
            col_secondary.desc() if desc_secondary else col_secondary.asc(),
        )
        rows = list(session.scalars(statement))
        if q:
            needle = q.casefold()
            rows = [
                row
                for row in rows
                if needle in row.file_name.casefold()
                or needle in row.kind.casefold()
                or needle in row.status.casefold()
            ]
        rows = _filter_batches_in_scope(session, rows, scope)
        start = (params.page - 1) * params.page_size
        return _page(
            params,
            [_batch_payload(row) for row in rows[start : start + params.page_size]],
            len(rows),
        )
    finally:
        session.close()


@router.get("/finance/imports/{id}")
@api_endpoint(
    entity="IngestBatch",
    action="IngestBatch.get",
    permission="integration:read",
    risk_tier="none",
    idempotency="none",
)
def get_import(
    request: Request,
    id: UUID,
    permission_service: PermissionService = Depends(get_permission_service),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _require(request, principal, "integration:read", entity="IngestBatch")
        scope = permission_service.store_scope(principal, "IngestBatch")
        batch = session.get(ImportBatch, id)
        if batch is None or not _batch_in_scope(session, batch.id, scope):
            raise not_found()
        return _batch_payload(batch)
    finally:
        session.close()


_MAX_UPLOAD_SIZE = 50 * 1024 * 1024


@router.post("/finance/imports", status_code=201)
@api_endpoint(
    entity="IngestBatch",
    action="IngestBatch.create",
    permission="integration:import",
    risk_tier="medium",
    idempotency="dispatcher",
)
async def create_import(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    _meta: Annotated[_FileMetaForm, Depends(_FileMetaForm.as_form)],
    permission_service: PermissionService = Depends(get_permission_service),
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        session.rollback()

        # 读取并验证文件
        filename = file.filename
        if filename is None:
            raise APIError(ErrorCode.VALIDATION_ERROR, "文件名不能为空", status_code=422)
        content = await file.read()
        if not content:
            raise APIError(ErrorCode.VALIDATION_ERROR, "文件不能为空", status_code=422)
        if len(content) > _MAX_UPLOAD_SIZE:
            raise APIError(ErrorCode.VALIDATION_ERROR, "文件超过 50MB 限制", status_code=422)

        # 店铺范围检查: 写入前验证
        scope = permission_service.store_scope(principal, "IngestBatch")
        if not isinstance(scope, AllStores) and not scope:
            raise APIError(ErrorCode.DATA_SCOPE_DENIED, "数据范围外无法导入", status_code=403)

        # 权限检查: 导入前验证
        _require(request, principal, "integration:import", entity="IngestBatch")

        file_sha256 = hashlib.sha256(content).hexdigest()

        with tempfile.TemporaryDirectory() as tmp:
            temp_path = Path(tmp) / filename
            temp_path.write_bytes(content)

            with session.begin():
                _reject_other_identity_key(session, principal, idempotency_key)
                # 运行导入创建批次 (在 dispatcher 事务内)
                try:
                    connector = detect(temp_path)
                    import_result = import_file(session, temp_path, connector)
                    batch_id = import_result.batch_id
                except DuplicateImportError:
                    # 同一文件哈希已成功导入, 查找已有批次
                    existing = session.scalar(
                        select(ImportBatch).where(ImportBatch.done_sha256 == file_sha256)
                    )
                    if existing is None:
                        raise
                    batch_id = existing.id
                    import_result = None

                def build_result() -> dict[str, Any]:
                    if import_result is not None:
                        return {
                            "batchId": str(batch_id),
                            "fileSha256": import_result.file_sha256,
                            "rowCount": import_result.row_count,
                            "errorCount": import_result.error_count,
                            "status": import_result.status.value,
                            "message": import_result.message,
                            "before": {"status": "superseded"},
                            "undo": {
                                "action": "IngestBatch.import",
                                "entity": "IngestBatch",
                                "id": str(batch_id),
                                "permission": "integration:import",
                                "expectedVersion": 1,
                            },
                        }
                    batch = session.get(ImportBatch, batch_id)
                    if batch is None:
                        raise not_found()
                    return {
                        "batchId": str(batch_id),
                        "fileSha256": batch.file_sha256,
                        "rowCount": batch.row_count,
                        "errorCount": batch.error_count,
                        "status": batch.status,
                        "message": None,
                        "before": {"status": "superseded"},
                        "undo": {
                            "action": "IngestBatch.import",
                            "entity": "IngestBatch",
                            "id": str(batch_id),
                            "permission": "integration:import",
                            "expectedVersion": batch.version,
                        },
                    }

                payload = {
                    "fileName": filename,
                    "fileSha256": file_sha256,
                    "fileSize": len(content),
                }

                result = make_action_dispatcher(
                    session,
                    request.app.state.permission_service,
                    undo_restore=CATALOG_UNDO_RESTORE,
                ).dispatch(
                    principal=principal,
                    permission="integration:import",
                    risk_tier=RiskTier.MEDIUM,
                    action="IngestBatch.create",
                    entity="IngestBatch",
                    entity_id=batch_id,
                    payload=payload,
                    idempotency_key=idempotency_key,
                    source_file=filename,
                    request_id=request.state.request_id,
                    business_action=build_result,
                )
            return dict(result)
    finally:
        session.close()


__all__ = ["router"]
