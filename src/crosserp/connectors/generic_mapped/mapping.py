"""YAML 列映射。校验结构。不读取表格。"""

from __future__ import annotations

import codecs
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml  # type: ignore[import-untyped]
from pydantic import Field, ValidationError, model_validator

from crosserp.core.models import ColumnMapping

TargetName = Literal["order_line", "sku_cost", "fx_rate", "sku"]

# 每个 target 允许的字段。不在表里的名字拒绝。不猜测。
_FIELDS: dict[str, frozenset[str]] = {
    "order_line": frozenset(
        {
            "platform_order_id",
            "order_item_id",
            "platform_sku",
            "qty",
            "order_date",
            "item_price",
            "currency",
            "store",
            "platform",
            "marketplace",
            "store_name",
            "store_currency",
        }
    ),
    "sku_cost": frozenset(
        {
            "internal_sku",
            "unit_cost",
            "freight_per_unit",
            "currency",
            "valid_from",
            "valid_to",
        }
    ),
    "fx_rate": frozenset({"period", "from_ccy", "to_ccy", "rate", "source"}),
    "sku": frozenset(
        {
            "platform_sku",
            "internal_sku",
            "title",
            "active",
            "store",
            "platform",
            "marketplace",
            "store_name",
            "store_currency",
        }
    ),
}

# 必须出现在 columns 或 defaults。店铺和币种允许默认值。
_REQUIRED: dict[str, tuple[str, ...]] = {
    "order_line": (
        "platform_order_id",
        "platform_sku",
        "qty",
        "order_date",
        "item_price",
        "currency",
        "store",
    ),
    "sku_cost": ("internal_sku", "unit_cost", "freight_per_unit", "currency", "valid_from"),
    "fx_rate": ("period", "from_ccy", "to_ccy", "rate"),
    "sku": ("platform_sku", "internal_sku", "store"),
}

_DATE_TARGETS = frozenset({"order_line", "sku_cost"})
_AMOUNT_TARGETS = frozenset({"order_line", "sku_cost", "fx_rate"})
_TODO_HINT = "请先填写真实表头"


class MappingError(ValueError):
    """映射不能用。消息用中文。"""


class MappingSpec(ColumnMapping):
    """经校验的映射。target 只能是四种标准记录。"""

    target: TargetName
    source_name: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def _check_spec(self) -> MappingSpec:
        todo = _todo_fields(self)
        if todo:
            names = "、".join(todo)
            raise ValueError(f"{_TODO_HINT}。这些映射仍是占位。{names}")
        unknown = [name for name in self.columns if name not in _FIELDS[self.target]]
        unknown.extend(name for name in self.defaults if name not in _FIELDS[self.target])
        if unknown:
            allowed = "、".join(sorted(_FIELDS[self.target]))
            names = "、".join(unknown)
            raise ValueError(f"不认识的映射字段 {names}。允许的字段是 {allowed}。不会猜测。")
        missing = [
            name
            for name in _REQUIRED[self.target]
            if name not in self.columns and name not in self.defaults
        ]
        if missing:
            names = "、".join(missing)
            raise ValueError(
                f"必填字段缺映射。{self.target} 需要 {names}。请写在 columns 或 defaults。"
            )
        if self.target in _DATE_TARGETS:
            if not self.timezone:
                raise ValueError("请在 YAML 里填写 timezone。源文件时间要转成 UTC。")
            if not self.date_formats:
                raise ValueError("请在 YAML 里填写 date_formats。")
            _require_zone(self.timezone)
        if self.target in _AMOUNT_TARGETS and self.amount_locale is None:
            raise ValueError("请在 YAML 里填写 amount_locale。金额按 us 或 eu 解析。")
        try:
            codecs.lookup(self.encoding)
        except LookupError as exc:
            raise ValueError(f"不认识的编码 {self.encoding}") from exc
        return self


def mappings_dir() -> Path:
    """包内 YAML 目录。"""
    return Path(__file__).resolve().parents[1] / "mappings"


def load_mapping(path: Path) -> MappingSpec:
    """从 UTF-8 YAML 加载映射。占位表头直接拒绝。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MappingError(f"无法读取映射文件 {path.name}。{exc}") from exc
    except UnicodeError as exc:
        raise MappingError(f"映射文件必须是 UTF-8。{path.name}。{exc}") from exc
    loaded: object = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise MappingError("映射文件必须是 YAML 对象。")
    try:
        return MappingSpec.model_validate(loaded)
    except ValidationError as exc:
        raise MappingError(_validation_message(exc)) from exc


def coerce_mapping(mapping: ColumnMapping | None) -> MappingSpec:
    """把导入器传入的映射收成 MappingSpec。未传则整批不能开始。"""
    if mapping is None:
        raise MappingError("必须显式提供映射文件。请使用 --type mapped --mapping。")
    if isinstance(mapping, MappingSpec):
        return mapping
    try:
        return MappingSpec.model_validate(mapping.model_dump())
    except ValidationError as exc:
        raise MappingError(_validation_message(exc)) from exc


def missing_headers(spec: MappingSpec, headers: list[str]) -> list[tuple[str, str]]:
    """columns 里有、文件表头里没有的字段。"""
    found = set(headers)
    missing: list[tuple[str, str]] = []
    for field, header in spec.columns.items():
        if header not in found:
            missing.append((field, header))
    return missing


def missing_header_message(missing: list[tuple[str, str]], headers: list[str]) -> str:
    """整批失败用的表头提示。包含实际表头。"""
    shown = "、".join(headers) if headers else "(空)"
    parts = [
        f"YAML 里的 {field} 对应的表头 {header} 在文件里不存在，文件实际表头是 {shown}"  # noqa: RUF001
        for field, header in missing
    ]
    return "。".join(parts) + "。"


def _todo_fields(spec: MappingSpec) -> list[str]:
    found: list[str] = []
    for name, header in spec.columns.items():
        if _is_todo(header):
            found.append(name)
    for name, value in spec.defaults.items():
        if _is_todo(value):
            found.append(name)
    return found


def _is_todo(value: str) -> bool:
    return value.strip().startswith("TODO_")


def _require_zone(name: str) -> None:
    try:
        ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"不认识的时区 {name}") from exc


def _validation_message(exc: ValidationError) -> str:
    text = str(exc)
    if _TODO_HINT in text:
        return f"{_TODO_HINT}。请把 YAML 右边的 TODO_ 换成导出文件里的真实表头。"
    errors = exc.errors()
    if not errors:
        return f"映射文件无效。{text}"
    first = errors[0].get("msg", text)
    if not isinstance(first, str):
        first = text
    cleaned = first.removeprefix("Value error, ")
    return f"映射文件无效。{cleaned}"


def field_text(spec: MappingSpec, payload: dict[str, str], field: str) -> str | None:
    """取一个标准字段的文本。列存在时不用 defaults 填补空单元格。"""
    if field in spec.columns:
        raw = payload.get(spec.columns[field], "")
        stripped = raw.strip()
        return stripped if stripped else None
    if field in spec.defaults:
        stripped = spec.defaults[field].strip()
        return stripped if stripped else None
    return None


def require_text(spec: MappingSpec, payload: dict[str, str], field: str) -> str:
    """必填单元格。空则抛中文错误。"""
    value = field_text(spec, payload, field)
    if value is None:
        header = spec.columns.get(field, field)
        raise ValueError(f"必填字段 {field} 为空。表头 {header}")
    return value
