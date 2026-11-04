"""业务审计上下文和事务内审计辅助器。"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from crosserp.audit.log import append


@dataclass(frozen=True)
class AuditContext:
    """一次命令或请求的操作者信息。"""

    actor_type: str = "system"
    actor_user_id: UUID | None = None
    actor_name: str | None = None
    actor_role: str | None = None
    request_id: str | None = None
    ip: str | None = None


@contextmanager
def audited(
    session: Session,
    context: AuditContext,
    *,
    action: str,
    target_type: str,
    target_id: str,
    before: object,
    after: object,
    **fields: object,
) -> Iterator[None]:
    """业务代码退出上下文时写审计；写失败会让外层事务回滚。"""  # noqa: RUF002
    yield
    append(
        session,
        context.actor_type,
        action,
        target_type,
        target_id,
        before,
        after,
        actor_user_id=context.actor_user_id,
        actor_name=context.actor_name,
        actor_role=context.actor_role,
        request_id=context.request_id,
        ip=context.ip,
        **fields,
    )
