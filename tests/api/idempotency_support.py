"""测试里后挂写接口的幂等依赖。生产代码不提供这条路径。"""

# 测试依赖需要在参数默认值调用 Depends。
# ruff: noqa: B008

from __future__ import annotations

from fastapi import Depends, Request

from crosserp.api.idempotency import RegisteredIdempotency, _replay_or_capture
from crosserp.platform.principal import Principal, get_principal


async def replay_ad_hoc_write(
    request: Request, principal: Principal = Depends(get_principal)
) -> None:
    request.app.state.permission_service.require(principal, "authenticated")
    route = request.scope["route"]
    registered = RegisteredIdempotency("http", "authenticated", route.path)
    await _replay_or_capture(request, principal, registered)
