from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from crosserp.api import install_api
from crosserp.api.errors import APIError, ErrorCode
from crosserp.api.schemas import Money, PageParams
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.session import make_engine, sqlite_file_url
from crosserp.iam.service import IAMService
from crosserp.platform.dispatcher import (
    ActionDispatcher,
    AutonomyDecision,
    RiskTier,
    can_ai_execute,
)
from crosserp.platform.permissions import DefaultPermissionService, PermissionDenied
from crosserp.platform.principal import ActorType, Principal
from tests.api.conftest import TestApprovalGateway


class _UnitPermissionService:
    def require(self, principal, permission, _resource=None) -> None:
        if (
            permission not in {"public", "authenticated"}
            and permission not in principal.permissions
        ):
            raise APIError(ErrorCode.FORBIDDEN, "无权执行该操作")

    def data_scope_filter(self, _principal, _entity):
        return {}

    def current_permissions(self, principal):
        return principal.permissions


def test_money_and_pagination_use_camel_case() -> None:
    assert Money(amountMinor=12300, currency="CNY").model_dump(by_alias=True) == {
        "amountMinor": 12300,
        "currency": "CNY",
    }
    assert PageParams(pageSize=200).page_size == 200


def test_ai_risk_cap_and_dispatch_stage_order() -> None:
    assert can_ai_execute(RiskTier.MEDIUM) is AutonomyDecision.EXECUTE
    assert can_ai_execute(RiskTier.HIGH) is AutonomyDecision.DRAFT_OR_APPROVAL
    assert can_ai_execute(RiskTier.CRITICAL) is AutonomyDecision.REJECT
    calls: list[str] = []
    dispatcher = ActionDispatcher(
        {name: (lambda name=name, **_: calls.append(name)) for name in ActionDispatcher.STAGES},
        permission_service=_UnitPermissionService(),
        approval_gateway=TestApprovalGateway(),
    )
    dispatcher.dispatch(
        principal=Principal(user_id=None),
        permission="public",
        risk_tier=RiskTier.NONE,
        action="Health.read",
        business_action=lambda: calls.append("business"),
    )
    assert calls == [*ActionDispatcher.STAGES[:5], "business", ActionDispatcher.STAGES[6]]


def test_permission_denial_uses_not_found_status(engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        service = DefaultPermissionService(IAMService(engine))
        service.require(Principal(user_id=uuid4(), roles=frozenset({"viewer"})), "user:write")
    except PermissionDenied as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("permission check unexpectedly passed")
    finally:
        downgrade_base(url)


def test_permission_denied_by_iam_is_not_granted_by_role_name(engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        service = DefaultPermissionService(IAMService(engine))
        with pytest.raises(PermissionDenied) as denied:
            service.require(Principal(user_id=uuid4(), roles=frozenset({"viewer"})), "user:read")
        assert denied.value.status_code == 404
    finally:
        downgrade_base(url)


def test_idempotency_replays_and_rejects_different_body() -> None:
    with TemporaryDirectory(prefix="crosserp-api-") as directory:
        url = sqlite_file_url(Path(directory) / "api.db")
        upgrade_head(url)
        engine = make_engine(url)
        app = FastAPI()
        install_api(app, engine)
        router = APIRouter()

        @router.post("/echo")
        def echo(payload: dict[str, Any]) -> dict[str, Any]:
            return payload

        app.include_router(router, prefix="/api/v1")
        with TestClient(app) as client:
            headers = {"Idempotency-Key": "api-test-key"}
            first = client.post("/api/v1/echo", json={"value": 1}, headers=headers)
            replay = client.post("/api/v1/echo", json={"value": 1}, headers=headers)
            conflict = client.post("/api/v1/echo", json={"value": 2}, headers=headers)
        engine.dispose()
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json() == {"value": 1}
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"
    assert conflict.json()["requestId"]


def test_agent_principal_keeps_human_identity() -> None:
    principal = Principal(
        user_id=None,
        actor_type=ActorType.AGENT,
        agent_id="agent-1",
        on_behalf_of=None,
    )
    assert principal.is_agent
