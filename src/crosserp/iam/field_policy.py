"""序列化阶段的字段裁剪钩子。"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from crosserp.iam.service import IAMService


def serialize_fields(
    service: IAMService,
    user_id: UUID,
    record: dict[str, Any],
    field_permissions: dict[str, str],
) -> dict[str, Any]:
    return service.serialize(user_id, record, field_permissions)


__all__ = ["serialize_fields"]
