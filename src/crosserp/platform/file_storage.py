"""平台文件对象存储。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FileStorage:
    """应用启动时注入的唯一文件存储根目录。"""

    root: Path

    def __post_init__(self) -> None:
        resolved = self.root.expanduser().resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        object.__setattr__(self, "root", resolved)

    def path_for(self, digest: str) -> Path:
        return self.root / digest

    def write(self, digest: str, content: bytes) -> Path:
        path = self.path_for(digest)
        path.write_bytes(content)
        return path


__all__ = ["FileStorage"]
