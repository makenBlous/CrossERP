"""模型 token 价格读取和 Decimal 费用计算。"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


def estimate_cost(
    model: str, input_tokens: int, output_tokens: int, path: Path | None = None
) -> Decimal | None:
    selected = path or Path.home() / ".crosserp" / "model_prices.yaml"
    if not selected.is_file():
        return None
    raw: Any = yaml.safe_load(selected.read_text(encoding="utf-8")) or {}
    item = raw.get("models", {}).get(model) if isinstance(raw, dict) else None
    if (
        not isinstance(item, dict)
        or not isinstance(item.get("input_per_million"), str)
        or not isinstance(item.get("output_per_million"), str)
    ):
        return None
    value = (
        Decimal(item["input_per_million"]) * input_tokens
        + Decimal(item["output_per_million"]) * output_tokens
    ) / Decimal(1_000_000)
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
