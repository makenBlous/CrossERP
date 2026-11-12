"""店铺范围缺规则时拒绝放行。"""

from uuid import uuid4

import pytest

from crosserp.api.errors import APIError, ErrorCode
from crosserp.platform.permissions import DefaultPermissionService
from crosserp.platform.principal import Principal


class _ScopeIam:
    def store_scope(self, _principal: Principal, _entity: str):
        raise APIError(ErrorCode.VALIDATION_FAILED, "店铺数据范围规则缺失")


def test_store_scope_does_not_invent_entity_id_keys() -> None:
    service = DefaultPermissionService(_ScopeIam())
    with pytest.raises(APIError) as exc_info:
        service.store_scope(Principal(user_id=uuid4()), "Sku")
    assert exc_info.value.code is ErrorCode.VALIDATION_FAILED
