"""智能体只读会话由 T30 实现，本任务保留严格 xfail 占位。"""  # noqa: RUF002

from __future__ import annotations

import pytest

pytestmark = pytest.mark.guard


@pytest.mark.xfail(strict=True, reason="T30 才实现智能体数据库只读会话")
def test_agent_session_rejects_write_until_t30() -> None:
    raise RuntimeError("T30 未实现")
