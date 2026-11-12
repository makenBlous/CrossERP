"""导入批次投射与替代重放。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.db.schema import (
    CleansingIssue,
    EntityEvent,
    ImportBatch,
    IngestProjection,
    MappingRule,
    RawRow,
    Sku,
)
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.principal import Principal


class _StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class ProjectionSpec(_StrictModel):
    entity: str = Field(min_length=1)
    action: str = Field(min_length=1)
    fields: dict[str, str] = Field(default_factory=dict)


class MappingRuleBody(_StrictModel):
    """投射使用的、已验证映射规则结构。"""

    required: list[str] = Field(default_factory=list)
    amount_fields: list[str] = Field(default_factory=list, alias="amountFields")
    period_field: str | None = Field(default=None, alias="periodField")
    direction_field: str | None = Field(default=None, alias="directionField")
    columns: dict[str, str] = Field(default_factory=dict)
    projection: ProjectionSpec


class _RawProjectionPayload(BaseModel):
    model_config = ConfigDict(strict=True, extra="allow")

    data: dict[str, Any] | None = None


class _SkuCreatePayload(_StrictModel):
    model_config = ConfigDict(strict=True, extra="allow")

    id: str | None = None
    store_id: str = Field(alias="storeId", min_length=1)
    platform_sku: str = Field(alias="platformSku", min_length=1)
    internal_sku: str = Field(alias="internalSku", min_length=1)
    title: str
    active: bool


class _DataScope(_StrictModel):
    entity: str | None = None
    scopes: list[str] = Field(default_factory=list)
    filters: dict[str, list[str]] = Field(default_factory=dict)


class _ProjectionResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="allow")

    posted: bool = False
    undo: dict[str, Any] | None = None


@dataclass(frozen=True)
class _ActionDefinition:
    permission: str
    risk_tier: RiskTier
    money: bool


_ACTION_DEFINITIONS: dict[tuple[str, str], _ActionDefinition] = {
    ("Sku", "Sku.create"): _ActionDefinition("item:create", RiskTier.MEDIUM, False),
    ("Sku", "Sku.update"): _ActionDefinition("item:write", RiskTier.MEDIUM, False),
    ("SkuCost", "SkuCost.create"): _ActionDefinition("item:write", RiskTier.HIGH, True),
    ("Settlement", "Settlement.split_draft_voucher"): _ActionDefinition(
        "journal_entry:create", RiskTier.HIGH, True
    ),
    ("Voucher", "Voucher.submit"): _ActionDefinition("journal_entry:submit", RiskTier.HIGH, True),
    ("Voucher", "Voucher.from_profit"): _ActionDefinition(
        "journal_entry:create", RiskTier.HIGH, True
    ),
    ("Voucher", "Voucher.from_order"): _ActionDefinition(
        "journal_entry:create", RiskTier.HIGH, True
    ),
    ("Voucher", "Voucher.reverse"): _ActionDefinition("journal_entry:write", RiskTier.HIGH, True),
    ("Voucher", "Voucher.update"): _ActionDefinition("journal_entry:write", RiskTier.HIGH, True),
    ("OpeningBatch", "OpeningBatch.activate"): _ActionDefinition(
        "journal_entry:submit", RiskTier.CRITICAL, True
    ),
}
_ACTION_PERMISSIONS = {
    action: definition.permission for (_entity, action), definition in _ACTION_DEFINITIONS.items()
}


def project_batch(
    session: Session,
    batch_id: UUID,
    *,
    principal: Principal,
    permission_service: Any,
    request_id: str | None,
    idempotency_key: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise not_found(message="导入批次不存在")
    if batch.status == "projected":
        rows = list(
            session.scalars(select(IngestProjection).where(IngestProjection.batch_id == batch.id))
        )
        return _project_result(batch, rows)
    if batch.status != "cleansed":
        raise APIError(ErrorCode.ILLEGAL_TRANSITION, "只有已清洗批次可以投射")
    rule = session.scalar(
        select(MappingRule).where(MappingRule.rule_version == batch.mapping_rule_version)
    )
    if rule is None or not rule.verified:
        raise APIError(ErrorCode.UNVERIFIED_RULE_VERSION, "批次绑定的映射规则未核实")
    rule_body = _parse_rule_body(rule.body_json)
    issue_rows = set(
        session.scalars(
            select(CleansingIssue.raw_record_id).where(
                CleansingIssue.batch_id == batch.id, CleansingIssue.status == "open"
            )
        )
    )
    raw_rows = list(
        session.scalars(select(RawRow).where(RawRow.batch_id == batch.id).order_by(RawRow.row_no))
    )
    projections: list[IngestProjection] = []
    dispatcher = make_action_dispatcher(session, permission_service)
    for raw in raw_rows:
        if raw.id in issue_rows:
            continue
        entity, action, data = _projection_spec(rule_body, raw.payload_json)
        definition = _ACTION_DEFINITIONS.get((entity, action))
        if definition is None:
            raise APIError(ErrorCode.VALIDATION_ERROR, "映射规则包含未登记的实体动作")
        _validate_data_scope(permission_service, principal, entity, action, data)
        existing = session.scalar(
            select(IngestProjection).where(
                IngestProjection.batch_id == batch.id,
                IngestProjection.raw_record_id == raw.id,
                IngestProjection.rule_version == rule.rule_version,
                IngestProjection.action_id == action,
            )
        )
        if existing is not None:
            projections.append(existing)
            continue
        entity_id = _entity_id(data)
        row_key = f"{idempotency_key}:{raw.id}" if idempotency_key else None

        def work(
            entity_name: str = entity,
            action_name: str = action,
            target_id: str = entity_id,
            row_data: dict[str, Any] = data,
            money_value: bool = definition.money,
        ) -> dict[str, Any]:
            return _apply_projection(
                session, entity_name, action_name, target_id, row_data, money_value
            )

        result = cast(
            dict[str, Any],
            dispatcher.dispatch(
                principal=principal,
                permission=definition.permission,
                risk_tier=definition.risk_tier,
                action=action,
                entity=entity,
                entity_id=entity_id,
                payload=data,
                idempotency_key=row_key,
                source_batch_id=batch.id,
                source_raw_row_id=raw.id,
                source_file=batch.file_name,
                source_rule_version=rule.rule_version,
                request_id=request_id,
                business_action=work,
            ),
        )
        item = IngestProjection(
            id=uuid4(),
            batch_id=batch.id,
            raw_record_id=raw.id,
            rule_version=rule.rule_version,
            entity_type=entity,
            entity_id=entity_id,
            action_id=action,
            status=str(result.get("status", "projected")),
            result_json=result,
            undo_payload_json=result.get("undo"),
            created_at=datetime.now(UTC),
        )
        session.add(item)
        session.flush()
        projections.append(item)
    batch.projected_count = sum(
        1 for row in projections if row.status in {"projected", "created", "succeeded"}
    )
    batch.status = "projected"
    batch.version += 1
    batch.counts_json = {
        "landed": batch.landed_count,
        "valid": batch.valid_count,
        "duplicate": batch.duplicate_count,
        "quarantined": batch.quarantined_count,
        "projected": batch.projected_count,
    }
    return _project_result(batch, projections)


def supersede_batch(
    session: Session,
    old_batch_id: UUID,
    *,
    new_batch_id: UUID,
    principal: Principal,
) -> dict[str, Any]:
    old = session.get(ImportBatch, old_batch_id)
    new = session.get(ImportBatch, new_batch_id)
    if old is None or new is None:
        raise not_found(message="导入批次不存在")
    if old.status != "projected":
        raise APIError(ErrorCode.ILLEGAL_TRANSITION, "只有已投射批次可以替代")
    if new.status not in {"cleansed", "projected"}:
        raise APIError(ErrorCode.ILLEGAL_TRANSITION, "替代批次必须已清洗或已投射")
    rows = list(
        session.scalars(
            select(IngestProjection).where(
                IngestProjection.batch_id == old.id, IngestProjection.compensated.is_(False)
            )
        )
    )
    now = datetime.now(UTC)
    for row in rows:
        result = _ProjectionResult.model_validate(row.result_json)
        session.add(
            EntityEvent(
                id=uuid4(),
                event_type="ingest_batch.projection.compensated",
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                action_id="IngestBatch.supersede",
                payload_json={
                    "oldBatchId": str(old.id),
                    "newBatchId": str(new.id),
                    "entityType": row.entity_type,
                    "entityId": row.entity_id,
                    "redLetter": result.posted,
                    "undo": row.undo_payload_json,
                },
                created_at=now,
            )
        )
        row.compensated = True
        row.compensated_at = now
    old.status = "superseded"
    old.version += 1
    new.supersedes_id = old.id
    new.version += 1
    return {
        "id": str(old.id),
        "newBatchId": str(new.id),
        "status": "superseded",
        "version": old.version,
        "compensated": len(rows),
        "undo": {"action": "IngestBatch.project", "batchId": str(old.id)},
    }


def _parse_rule_body(value: Any) -> MappingRuleBody:
    try:
        return MappingRuleBody.model_validate(value)
    except ValidationError as exc:
        raise APIError(
            ErrorCode.VALIDATION_ERROR,
            "映射规则结构无效",
            details={"errors": exc.errors()},
        ) from exc


def _projection_spec(rule_body: MappingRuleBody, payload: Any) -> tuple[str, str, dict[str, Any]]:
    try:
        source = _RawProjectionPayload.model_validate(payload)
    except ValidationError as exc:
        raise APIError(
            ErrorCode.VALIDATION_ERROR,
            "原始记录结构无效",
            details={"errors": exc.errors()},
        ) from exc
    data = (
        dict(source.data)
        if source.data is not None
        else dict(cast(dict[str, Any], source.model_extra))
    )
    mapped = dict(data)
    for target, source_name in rule_body.projection.fields.items():
        if source_name not in data:
            raise APIError(ErrorCode.VALIDATION_ERROR, f"原始记录缺少字段: {source_name}")
        mapped[target] = data[source_name]
    return rule_body.projection.entity, rule_body.projection.action, mapped


def _entity_id(data: dict[str, Any]) -> str:
    value = data.get("id")
    return str(value) if value else str(uuid4())


def _validate_data_scope(
    permission_service: Any, principal: Principal, entity: str, action: str, data: dict[str, Any]
) -> None:
    if entity != "Sku" or action != "Sku.create":
        return
    try:
        sku = _SkuCreatePayload.model_validate(data)
        store_id = UUID(sku.store_id)
    except (ValidationError, ValueError) as exc:
        raise APIError(ErrorCode.VALIDATION_ERROR, "Sku.create 数据无效") from exc
    try:
        scope = _DataScope.model_validate(permission_service.data_scope_filter(principal, "Sku"))
    except ValidationError as exc:
        raise APIError(ErrorCode.INTERNAL_ERROR, "数据范围协议返回无效") from exc
    store_ids = scope.filters.get("storeIds")
    if store_ids is not None and str(store_id) not in store_ids:
        raise APIError(
            ErrorCode.DATA_SCOPE_DENIED,
            "目标店铺超出数据范围",
            details={"entity": "Sku", "storeId": str(store_id)},
            status_code=403,
        )


def _apply_projection(
    session: Session,
    entity: str,
    action: str,
    entity_id: str,
    data: dict[str, Any],
    money: bool,
) -> dict[str, Any]:
    if money:
        return {
            "id": entity_id,
            "status": "draft",
            "draft": True,
            "undo": {"action": "draft.discard", "entityType": entity, "entityId": entity_id},
            "after": data,
        }
    if entity == "Sku" and action == "Sku.create":
        try:
            sku = _SkuCreatePayload.model_validate(data)
            store_id = UUID(sku.store_id)
            entity_uuid = UUID(entity_id)
        except (ValidationError, ValueError) as exc:
            raise APIError(ErrorCode.VALIDATION_ERROR, "Sku.create 数据无效") from exc
        row = session.scalar(
            select(Sku).where(Sku.store_id == store_id, Sku.platform_sku == sku.platform_sku)
        )
        if row is None:
            row = Sku(
                id=entity_uuid,
                store_id=store_id,
                platform_sku=sku.platform_sku,
                internal_sku=sku.internal_sku,
                title=sku.title,
                active=sku.active,
            )
            session.add(row)
            session.flush()
        return {
            "id": str(row.id),
            "status": "created",
            "after": {
                "storeId": str(row.store_id),
                "platformSku": row.platform_sku,
                "internalSku": row.internal_sku,
                "title": row.title,
                "active": row.active,
            },
            "undo": {"action": "Sku.delete", "entityId": str(row.id)},
        }
    raise APIError(ErrorCode.VALIDATION_ERROR, f"暂不支持投射动作: {action}")


def _project_result(batch: ImportBatch, rows: list[IngestProjection]) -> dict[str, Any]:
    return {
        "id": str(batch.id),
        "status": "projected",
        "version": batch.version,
        "projected": batch.projected_count,
        "items": [
            {
                "rawRecordId": row.raw_record_id,
                "entityType": row.entity_type,
                "entityId": row.entity_id,
                "action": row.action_id,
                "status": row.status,
                "result": row.result_json,
                "undo": row.undo_payload_json,
            }
            for row in rows
        ],
    }


__all__ = ["MappingRuleBody", "project_batch", "supersede_batch"]
