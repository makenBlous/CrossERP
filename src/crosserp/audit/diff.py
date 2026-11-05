"""审计记录的改前/改后字段差异计算。  # noqa: RUF002

差异在后端计算, 网页只负责渲染结果。对象中的字典会递归展开, 列表和
标量按一个字段比较, 以保证输出稳定且不会把任何业务金额重新计算。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class FieldDiff:
    """一个字段的变化。``change`` 取 added/deleted/modified。"""

    path: str
    before: Any
    after: Any
    change: str

    @property
    def kind(self) -> str:
        """兼容模板和调用方使用的变化类型名称。"""
        return self.change

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def diff(before: Any, after: Any) -> list[FieldDiff]:
    """返回按字段路径排序的改前/改后差异。"""
    result: list[FieldDiff] = []
    _walk(before, after, "", result)
    return sorted(result, key=lambda item: item.path)


def diff_json(before: Any, after: Any) -> list[dict[str, Any]]:
    """以模板友好的字典形式返回差异。"""
    return [item.as_dict() for item in diff(before, after)]


# 这些别名让纯函数可从不同层调用，同时保持一个实现。  # noqa: RUF003
compute_diff = diff
compare = diff


def _walk(before: Any, after: Any, path: str, result: list[FieldDiff]) -> None:
    if isinstance(before, dict) and isinstance(after, dict):
        keys = sorted(set(before) | set(after), key=str)
        for key in keys:
            child = f"{path}.{key}" if path else str(key)
            if key not in before:
                result.append(FieldDiff(child, None, after[key], "added"))
            elif key not in after:
                result.append(FieldDiff(child, before[key], None, "deleted"))
            else:
                _walk(before[key], after[key], child, result)
        return
    if before != after:
        result.append(FieldDiff(path or "$", before, after, "modified"))
