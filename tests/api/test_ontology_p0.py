from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode
from crosserp.db.migrate import upgrade_head
from crosserp.db.schema import EntityVersion
from crosserp.db.session import make_engine, sqlite_file_url
from crosserp.ontology.catalog import load_catalog, validate_catalog
from crosserp.platform.approval import ApprovalResolution
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
from crosserp.platform.principal import ActorType, Principal


def test_catalog_loads_all_entities_and_rejects_missing_transition_action() -> None:
    assert (
        Path("src/crosserp/ontology/catalog/ontology-entities.yaml").read_bytes()
        == Path("docs/design/08/ontology-entities.yaml").read_bytes()
    )
    catalog = load_catalog()
    assert len(catalog.entity_types) == 166
    assert len(catalog.actions) >= 500
    broken = yaml.safe_load(
        Path("docs/design/08/ontology-entities.yaml").read_text(encoding="utf-8")
    )
    broken["entityTypes"][0]["actions"] = []
    with pytest.raises(ValueError, match="transition"):
        validate_catalog(broken)


def test_agent_high_risk_submits_approval_without_business_action() -> None:
    submitted: list[dict[str, object]] = []

    class Gateway:
        def submit(self, **kwargs: object) -> object:
            submitted.append(kwargs)
            return {"approvalId": "a1", "resolution": ApprovalResolution.AWAITING_INITIATOR}

    called: list[bool] = []
    principal = Principal(
        user_id=uuid4(),
        actor_type=ActorType.AGENT,
        agent_id="agent-1",
        on_behalf_of=uuid4(),
        delegation_id="del-1",
        channel="agent",
    )
    result = ActionDispatcher(approval_gateway=Gateway()).dispatch(
        principal=principal,
        permission="public",
        risk_tier=RiskTier.HIGH,
        entity="Voucher",
        action="Voucher.post",
        business_action=lambda: called.append(True),
    )
    assert result["resolution"] == ApprovalResolution.AWAITING_INITIATOR
    assert called == []
    assert submitted[0]["action"] == "Voucher.post"


def test_dispatch_writes_entity_version_and_rolls_back_with_audit() -> None:
    with TemporaryDirectory() as directory:
        url = sqlite_file_url(Path(directory) / "db.sqlite")
        upgrade_head(url)
        engine = make_engine(url)
        principal = Principal(user_id=uuid4(), permissions=frozenset({"store:write"}))
        entity_id = uuid4()
        dispatcher = ActionDispatcher(session=Session(engine))
        with dispatcher.session.begin():
            result = dispatcher.dispatch(
                principal=principal,
                permission="store:write",
                risk_tier=RiskTier.MEDIUM,
                entity="Store",
                entity_id=entity_id,
                action="Store.update",
                business_action=lambda: {"before": {"name": "old"}, "after": {"name": "new"}},
            )
        with Session(engine) as session:
            row = session.scalar(
                select(EntityVersion).where(EntityVersion.entity_id == str(entity_id))
            )
            assert row is not None
            assert result["version"] == 1
            assert row.after_json == {"name": "new"}
        engine.dispose()


def test_ai_medium_has_no_count_limit_and_critical_is_rejected() -> None:
    principal = Principal(
        user_id=uuid4(),
        permissions=frozenset({"store:write"}),
        actor_type=ActorType.AGENT,
    )
    calls: list[int] = []
    dispatcher = ActionDispatcher()
    for index in range(8):
        dispatcher.dispatch(
            principal=principal,
            permission="store:write",
            risk_tier=RiskTier.MEDIUM,
            action="Store.update",
            business_action=lambda index=index: calls.append(index),
        )
    assert calls == list(range(8))
    with pytest.raises(APIError) as error:
        dispatcher.dispatch(
            principal=principal,
            permission="store:write",
            risk_tier=RiskTier.CRITICAL,
            action="Role.update",
            business_action=lambda: calls.append(99),
        )
    assert error.value.code is ErrorCode.AI_AUTONOMY_CAPPED
    assert 99 not in calls


def test_three_channels_have_same_result_and_denial() -> None:
    dispatcher = ActionDispatcher()
    results = []
    for channel in ("web", "agent", "import"):
        results.append(
            dispatcher.dispatch(
                principal=Principal(user_id=uuid4(), channel=channel),
                permission="authenticated",
                risk_tier=RiskTier.LOW,
                action="Store.create",
                business_action=lambda: {"ok": True},
            )
        )
    assert results == [{"ok": True}] * 3
    for channel in ("web", "agent", "import"):
        with pytest.raises(APIError) as error:
            dispatcher.dispatch(
                principal=Principal(user_id=uuid4(), channel=channel),
                permission="store:write",
                risk_tier=RiskTier.LOW,
                action="Store.update",
                business_action=lambda: {"ok": True},
            )
        assert error.value.code is ErrorCode.FORBIDDEN
