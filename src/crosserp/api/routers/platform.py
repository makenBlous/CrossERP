"""Compatibility import for platform common helpers."""

from ._platform_common import (
    _db,
    _dispatch_write,
    _jsonable,
    _page,
    _permission_service,
    _principal_db,
    _require,
    _user,
    _write_guard,
    router,
)

__all__ = ["router"]
