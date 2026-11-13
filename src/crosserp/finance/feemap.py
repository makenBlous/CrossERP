"""确认费用分类。高风险动作按审批结果生效。智能体只生成审批。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from pydantic import Field, StrictInt
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.schemas import CamelModel
from crosserp.catalog.undo_restore import CATALOG_UNDO_RESTORE
from crosserp.db.schema import MappingRule
from crosserp.iam.scope import AllStores, store_contains
from crosserp.platform.dispatcher import RiskTier
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal


class FeeMapConfirmBody(CamelModel):
    """确认费用分类的动作输入。"""

    expected_version: StrictInt | None = Field(default=None, alias="expectedVersion", ge=0)
    comment: str | None = Field(default=None)
    reason: str | None = Field(default=None)


def confirm_fee_map(
    session: Session,
    rule_id: UUID,
    *,
    principal: Principal,
    permission_service: PermissionService,
    body: FeeMapConfirmBody,
    idempotency_key: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    """确认一条费用映射。审批通过前不把规则标成已确认。"""
    row = session.get(MappingRule, rule_id)
    if row is None or row.kind != "fee":
        raise not_found()
    payload = body.model_dump(by_alias=True, mode="json")
    payload["id"] = str(rule_id)
    dispatcher = make_action_dispatcher(
        session, permission_service, undo_restore=CATALOG_UNDO_RESTORE
    )

    def before_replay(**_context: Any) -> None:
        _require_scope(permission_service, principal, row.body_json)
        if principal.is_agent and _version_conflicts(body.expected_version, row.version):
            raise _version_error(body.expected_version, row.version)

    def business_action() -> dict[str, Any]:
        if _version_conflicts(body.expected_version, row.version):
            raise _version_error(body.expected_version, row.version)
        approval = dispatcher.approval_gateway.submit(
            principal=principal,
            entity="MappingRule",
            action="MappingRule.confirm",
            payload=payload,
            risk_tier=RiskTier.HIGH.value,
            approval_type="mappingrule",
            request_id=request_id,
        )
        if approval.state != "auto_effective":
            return {
                "id": str(row.id),
                "verified": row.verified,
                "applied": False,
                **approval.to_payload(),
            }
        row.verified = True
        row.version += 1
        row.updated_at = datetime.now(UTC)
        session.flush()
        return {
            "id": str(row.id),
            "ruleKey": row.rule_key,
            "kind": row.kind,
            "ruleVersion": row.rule_version,
            "status": row.status,
            "verified": True,
            "applied": True,
            "version": row.version,
            **approval.to_payload(),
        }

    return cast(
        dict[str, Any],
        dispatcher.dispatch(
            principal=principal,
            permission="integration:write",
            risk_tier=RiskTier.HIGH,
            action="MappingRule.confirm",
            entity="MappingRule",
            entity_id=rule_id,
            payload=payload,
            idempotency_key=idempotency_key,
            request_id=request_id,
            hooks={"idempotency_and_version": before_replay},
            business_action=business_action,
        ),
    )


def _require_scope(permission_service: PermissionService, principal: Principal, body: Any) -> None:
    scope = permission_service.store_scope(principal, "MappingRule")
    store_id = _store_id(body)
    if store_id is not None:
        if store_contains(scope, store_id):
            return
        raise APIError(ErrorCode.DATA_SCOPE_DENIED, "超出店铺数据范围")
    if isinstance(scope, AllStores):
        return
    raise APIError(ErrorCode.DATA_SCOPE_DENIED, "超出店铺数据范围")


def _store_id(body: Any) -> UUID | None:
    if "storeId" not in body:
        return None
    try:
        return UUID(str(body["storeId"]))
    except ValueError as exc:
        raise APIError(ErrorCode.VALIDATION_FAILED, "费用映射 storeId 无效") from exc


def _version_conflicts(expected: int | None, actual: int) -> bool:
    return expected is not None and expected != actual


def _version_error(expected: int | None, actual: int) -> APIError:
    return APIError(
        ErrorCode.CONFLICT_VERSION,
        "实体版本已变化",
        details={"expectedVersion": expected, "actualVersion": actual},
    )


__all__ = ["FeeMapConfirmBody", "confirm_fee_map"]
