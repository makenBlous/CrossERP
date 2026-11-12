"""导入批次投射与替代重放。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.approval.gateway import ApprovalGatewayImpl
from crosserp.db.schema import (
    CleansingIssue,
    EntityEvent,
    ImportBatch,
    IngestProjection,
    MappingRule,
    RawRow,
    Sku,
)
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
from crosserp.platform.principal import Principal

_MONEY_ENTITIES = {
    "Settlement",
    "SettlementLine",
    "Voucher",
    "VoucherLine",
    "CashTransaction",
    "Payment",
    "JournalEntry",
    "OpeningBatch",
    "SkuCost",
    "FeeReference",
}
_ACTION_PERMISSIONS = {
    "Sku.create": "item:create",
    "Sku.update": "item:write",
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
    if rule is None:
        raise APIError(ErrorCode.UNVERIFIED_RULE_VERSION, "批次绑定的映射规则不存在")
    rule_body = rule.body_json if isinstance(rule.body_json, dict) else {}
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
    for raw in raw_rows:
        if raw.id in issue_rows:
            continue
        entity, action, data = _projection_spec(batch, rule_body, raw.payload_json)
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
        permission = str(
            data.get("permission") or _ACTION_PERMISSIONS.get(action, "integration:import")
        )
        money = bool(data.get("moneyImpact", False)) or entity in _MONEY_ENTITIES
        risk = RiskTier.HIGH if money else RiskTier.MEDIUM
        row_key = f"{idempotency_key}:{raw.id}" if idempotency_key else None
        dispatcher = ActionDispatcher(
            session=session,
            permission_service=permission_service,
            approval_gateway=ApprovalGatewayImpl(session),
        )

        def work(
            entity_name: str = entity,
            action_name: str = action,
            target_id: str = entity_id,
            row_data: dict[str, Any] = data,
            money_value: bool = money,
        ) -> dict[str, Any]:
            return _apply_projection(
                session, entity_name, action_name, target_id, row_data, money_value
            )

        result = dispatcher.dispatch(
            principal=principal,
            permission=permission,
            risk_tier=risk,
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
        )
        item = IngestProjection(
            id=uuid4(),
            batch_id=batch.id,
            raw_record_id=raw.id,
            rule_version=rule.rule_version,
            entity_type=entity,
            entity_id=entity_id,
            action_id=action,
            status=str(result.get("status", "projected"))
            if isinstance(result, dict)
            else "projected",
            result_json=result,
            undo_payload_json=result.get("undo") if isinstance(result, dict) else None,
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
        result = row.result_json if isinstance(row.result_json, dict) else {}
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
                    "redLetter": bool(result.get("posted", False)),
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


def _projection_spec(
    batch: ImportBatch, rule_body: dict[str, Any], payload: Any
) -> tuple[str, str, dict[str, Any]]:
    source = payload if isinstance(payload, dict) else {}
    projection = rule_body.get("projection")
    spec: dict[str, Any] = projection if isinstance(projection, dict) else {}
    entity = str(spec.get("entity") or source.get("entityType") or source.get("entity") or "")
    if not entity and batch.kind.casefold() in {"sku", "catalog_sku", "sku_mapping"}:
        entity = "Sku"
    action = str(spec.get("action") or source.get("actionId") or source.get("action") or "")
    if not action and entity:
        action = f"{entity}.create"
    fields_value = spec.get("fields")
    fields: dict[str, Any] = fields_value if isinstance(fields_value, dict) else {}
    source_data = source.get("data")
    data: dict[str, Any] = dict(source_data) if isinstance(source_data, dict) else dict(source)
    mapped = dict(data)
    for target, source_name in fields.items():
        mapped[str(target)] = data.get(str(source_name))
    if not entity or not action:
        raise APIError(ErrorCode.VALIDATION_ERROR, "原始记录缺少投射实体动作")
    return entity, action, mapped


def _entity_id(data: dict[str, Any]) -> str:
    value = data.get("id")
    return str(value) if value else str(uuid4())


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
        store_id = UUID(str(data["storeId"]))
        platform_sku = str(data["platformSku"])
        row = session.scalar(
            select(Sku).where(Sku.store_id == store_id, Sku.platform_sku == platform_sku)
        )
        if row is None:
            row = Sku(
                id=UUID(entity_id),
                store_id=store_id,
                platform_sku=platform_sku,
                internal_sku=str(data["internalSku"]),
                title=str(data.get("title", "")),
                active=bool(data.get("active", True)),
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


__all__ = ["project_batch", "supersede_batch"]
