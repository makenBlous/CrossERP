"""写出目标协议。"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from sqlalchemy.orm import Session


class LedgerTarget(Protocol):
    """生成一个不可覆盖的外部产物。"""

    id: str

    def render(
        self,
        session: Session,
        *,
        batch_id: str,
        approval_id: str,
        output_dir: Path,
    ) -> Path:
        """写文件并返回文件路径。"""
