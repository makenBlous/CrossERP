"""原因码目录加载、校验和中文说明渲染。"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from crosserp.core.enums import IssueKind

_LOG = logging.getLogger(__name__)
_PATH = Path(__file__).with_name("catalog.yaml")


@dataclass(frozen=True)
class IssueDefinition:
    """一个原因码的展示和匹配率元数据。"""

    kind: str
    name_zh: str
    severity: str
    counts_as_unmatched: bool
    template_zh: str
    action_zh: str


def _read(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or not isinstance(loaded.get("codes"), list):
        raise ValueError(f"原因码目录格式错误: {path}")
    return loaded


def load_catalog(path: Path = _PATH) -> dict[str, IssueDefinition]:
    """加载并校验目录, 确保和 IssueKind 一一对应。"""
    definitions: dict[str, IssueDefinition] = {}
    for raw in _read(path)["codes"]:
        if not isinstance(raw, dict):
            raise ValueError(f"原因码目录有非对象条目: {path}")
        kind = raw.get("kind", raw.get("code"))
        name = raw.get("name_zh")
        severity = raw.get("severity")
        effect = raw.get("match_rate_effect")
        counts = raw.get("counts_as_unmatched", effect == "unmatched")
        templates = raw.get("templates")
        action = raw.get("action_zh", raw.get("action"))
        if (
            not isinstance(kind, str)
            or not isinstance(name, str)
            or not isinstance(severity, str)
            or not isinstance(counts, bool)
            or not isinstance(templates, list)
            or not templates
            or not isinstance(action, str)
        ):
            raise ValueError(f"原因码目录条目不完整: {raw!r}")
        first = templates[0]
        template = raw.get("template_zh")
        if not isinstance(template, str):
            template = first.get("text") if isinstance(first, dict) else None
        if not isinstance(template, str):
            raise ValueError(f"原因码目录模板错误: {kind}")
        if kind in definitions:
            raise ValueError(f"原因码重复: {kind}")
        definitions[kind] = IssueDefinition(
            kind=kind,
            name_zh=name,
            severity=severity,
            counts_as_unmatched=counts,
            template_zh=template,
            action_zh=action,
        )
    enum_values = {item.value for item in IssueKind}
    if set(definitions) != enum_values:
        missing = sorted(enum_values - set(definitions))
        extra = sorted(set(definitions) - enum_values)
        raise ValueError(f"原因码目录与枚举不一致。缺少={missing} 多出={extra}")
    return definitions


CATALOG = load_catalog()


def definition(kind: str | IssueKind) -> IssueDefinition:
    """读取一个原因码定义。"""
    value = kind.value if isinstance(kind, IssueKind) else kind
    try:
        return CATALOG[value]
    except KeyError as exc:
        raise ValueError(f"不认识的原因码: {value}") from exc


def render(issue: object, detail: Mapping[str, object] | None = None) -> str:
    """渲染异常的人话; 缺少字段时保留可读的缺失提示。"""
    if isinstance(issue, (str, IssueKind)):
        kind = issue.value if isinstance(issue, IssueKind) else issue
        values = {} if detail is None else dict(detail)
    else:
        kind = str(getattr(issue, "kind"))  # noqa: B009
        raw = getattr(issue, "detail_json", {})
        values = dict(raw) if isinstance(raw, Mapping) else {}
    item = definition(kind)

    class _Values(dict[str, object]):
        def __missing__(self, key: str) -> str:
            _LOG.warning("原因码 %s 缺少模板字段 %s", kind, key)
            return f"{{缺:{key}}}"

    return item.template_zh.format_map(_Values(values))
