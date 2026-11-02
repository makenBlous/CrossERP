"""从 entry point 发现连接器。按 sniff 分数识别文件。"""

from __future__ import annotations

from collections.abc import Sequence
from importlib.metadata import entry_points
from pathlib import Path

from crosserp.connectors.base import FileConnector
from crosserp.core.errors import UnknownFileTypeError

CONNECTOR_GROUP = "crosserp.connectors"
_MIN_SCORE = 0.5


def load_connectors() -> list[FileConnector]:
    """加载 crosserp.connectors 组里的连接器。类会无参实例化。"""
    found: list[FileConnector] = []
    seen: set[str] = set()
    for entry in entry_points(group=CONNECTOR_GROUP):
        loaded = entry.load()
        connector = _as_connector(loaded, entry.name)
        if connector.id in seen:
            raise TypeError(f"连接器 id 重复 {connector.id}")
        seen.add(connector.id)
        found.append(connector)
    return found


def detect(path: Path, connectors: Sequence[FileConnector] | None = None) -> FileConnector:
    """取 sniff 最高分。低于 0.5 或并列时要求调用方用 --type 指定。"""
    found = list(connectors) if connectors is not None else load_connectors()
    label = path.name
    if not found:
        raise UnknownFileTypeError(label, "没有已注册的连接器。")
    scored = [(item.sniff(path), item) for item in found]
    best = max(score for score, _item in scored)
    winners = [item for score, item in scored if score == best]
    if best < _MIN_SCORE:
        raise UnknownFileTypeError(label, f"最高识别分 {best} 低于 0.5。")
    if len(winners) != 1:
        names = "、".join(item.id for item in winners)
        raise UnknownFileTypeError(label, f"多个连接器同分 {names}。")
    return winners[0]


def _as_connector(loaded: object, name: str) -> FileConnector:
    candidate = loaded() if isinstance(loaded, type) else loaded
    if isinstance(candidate, FileConnector):
        return candidate
    raise TypeError(f"入口 {name} 不是 FileConnector")
