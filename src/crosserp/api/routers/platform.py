"""Compatibility import for platform common helpers."""

# Re-exported private helpers are consumed by the split feature routers.
# ruff: noqa: F401

from ._platform_common import (
    _db,
    _dispatch_write,
    _dispatcher,
    _jsonable,
    _page,
    _permission_service,
    _principal_db,
    _require,
    _user,
    _user_payload,
    _write_guard,
    router,
)

__all__ = [
    "router",
    "_db",
    "_dispatch_write",
    "_dispatcher",
    "_page",
    "_permission_service",
    "_principal_db",
    "_require",
    "_user",
    "_user_payload",
    "_write_guard",
]
