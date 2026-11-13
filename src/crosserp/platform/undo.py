"""撤销恢复注册表协议。平台只依赖这个协议。"""

from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy.orm import Session

from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal


class UndoRestoreRegistry(Protocol):
    """按实体回退字段或执行新建动作声明的反向动作。"""

    def supports(self, entity_type: str) -> bool: ...

    def restorable_fields(self, entity_type: str) -> frozenset[str]: ...

    def restore(
        self, session: Session, entity_type: str, entity_id: str, before: dict[str, Any]
    ) -> None: ...

    def apply_reverse(
        self,
        session: Session,
        *,
        action: str,
        entity_id: str,
        payload: dict[str, Any],
        principal: Principal,
        permission_service: PermissionService,
    ) -> dict[str, Any]: ...
