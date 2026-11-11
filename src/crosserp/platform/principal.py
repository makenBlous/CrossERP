"""当前请求的真人/智能体身份。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.auth.sessions import find_user
from crosserp.auth.tokens import authenticate
from crosserp.db.schema import UserRole


class ActorType(StrEnum):
    HUMAN = "human"
    AGENT = "agent"


@dataclass(frozen=True)
class Principal:
    user_id: UUID | None = None
    roles: frozenset[str] = field(default_factory=frozenset)
    session_id: str | None = None
    actor_type: ActorType = ActorType.HUMAN
    agent_id: str | None = None
    on_behalf_of: UUID | None = None
    delegation_id: str | None = None
    run_id: str | None = None
    is_subagent: bool = False
    channel: str = "web"
    permissions: frozenset[str] = field(default_factory=frozenset)
    # 由委托通行证签发时带入的被代表人当前有效权限快照。
    # 真实权限服务可在每次动作前覆盖该快照; 避免复用已撤回权限
    represented_permissions: frozenset[str] | None = None
    data_scope: Any = None

    @property
    def effective_user_id(self) -> UUID | None:
        return self.on_behalf_of or self.user_id

    @property
    def is_agent(self) -> bool:
        return self.actor_type is ActorType.AGENT


def principal_from_session(session: Session, request: Request) -> Principal | None:
    token = request.cookies.get("crosserp_session")
    api_token = request.headers.get("Authorization", "")
    user = None
    session_id = None
    if token:
        user = find_user(session, token)
        session_id = token[:16] if user is not None else None
    elif api_token.casefold().startswith("bearer "):
        auth = authenticate(session, api_token[7:].strip())
        if auth is not None:
            _token, user = auth
            session_id = str(_token.id)
    if user is None:
        return None
    return Principal(
        user_id=user.id,
        roles=frozenset(session.scalars(select(UserRole.role).where(UserRole.user_id == user.id))),
        session_id=session_id,
        channel="web" if token else "mcp",
    )


def get_principal(request: Request) -> Principal:
    """FastAPI 依赖: 先接现有 cookie 会话和 Bearer API Token。"""
    engine = getattr(request.app.state, "database_engine", None)
    if engine is None:
        from crosserp.api.errors import APIError, ErrorCode

        raise APIError(ErrorCode.AUTH_REQUIRED, "需要登录")
    with Session(engine) as session:
        principal = principal_from_session(session, request)
    if principal is None:
        from crosserp.api.errors import APIError, ErrorCode

        raise APIError(ErrorCode.AUTH_REQUIRED, "需要登录")
    return principal


__all__ = ["ActorType", "Principal", "get_principal", "principal_from_session"]
