"""JSON 客户端、隔离数据库和身份夹具。"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crosserp.db.repo.users import create_user, grant_role
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.session import make_engine, sqlite_file_url
from crosserp.platform.principal import ActorType, Principal
from crosserp.web.app import create_app


@pytest.fixture
def api_database(tmp_path: Path) -> str:
    return os.environ.get("CROSSERP_TEST_DATABASE_URL") or sqlite_file_url(tmp_path / "api.db")


@pytest.fixture
def api_engine(api_database: str):
    engine = make_engine(api_database)
    upgrade_head(api_database)
    try:
        yield engine
    finally:
        downgrade_base(api_database)
        engine.dispose()


@pytest.fixture
def json_client(api_database: str) -> Iterator[TestClient]:
    with TestClient(create_app(api_database)) as client:
        yield client


@pytest.fixture
def api_client(json_client: TestClient) -> TestClient:
    return json_client


@pytest.fixture
def principal_for_role() -> Callable[[str], Principal]:
    def factory(role: str) -> Principal:
        return Principal(user_id=uuid4(), roles=frozenset({role}))

    return factory


@pytest.fixture
def human_principal(principal_for_role: Callable[[str], Principal]) -> Principal:
    return principal_for_role("operator")


@pytest.fixture
def agent_principal(human_principal: Principal) -> Principal:
    return Principal(
        user_id=human_principal.user_id,
        roles=human_principal.roles,
        actor_type=ActorType.AGENT,
        agent_id="test-agent",
        on_behalf_of=human_principal.user_id,
        channel="mcp",
    )


@pytest.fixture
def logged_in_principal(api_engine) -> Callable[[str], Principal]:
    """创建一个已落库的角色用户并返回可用于依赖覆盖的 Principal 工厂。"""

    def factory(role: str) -> Principal:
        with Session(api_engine) as session, session.begin():
            user = create_user(
                session,
                username=f"api-{uuid4().hex[:12]}",
                password="Api-test-password-123",
                roles=(),
            )
            grant_role(session, user.id, role)
            return Principal(user_id=user.id, roles=frozenset({role}))

    return factory
