"""AI 调用统计。"""

from __future__ import annotations

from decimal import Decimal
from statistics import quantiles
from typing import Any

from crosserp.db.schema import LlmCall


def summarize(rows: list[LlmCall]) -> dict[str, Any]:
    latencies = sorted(row.latency_ms for row in rows)
    return {
        "calls": len(rows),
        "ok": sum(row.status == "ok" for row in rows),
        "refused": sum(row.status == "refused" for row in rows),
        "error": sum(row.status == "error" for row in rows),
        "input_tokens": sum(row.input_tokens for row in rows),
        "output_tokens": sum(row.output_tokens for row in rows),
        "cost": sum((row.cost_estimate or Decimal(0) for row in rows), Decimal(0)),
        "p50_ms": _percentile(latencies, 0.50),
        "p95_ms": _percentile(latencies, 0.95),
        "slowest": sorted(rows, key=lambda row: row.latency_ms, reverse=True)[:20],
    }


def _percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    if len(values) == 1:
        return values[0]
    return round(quantiles(values, n=100, method="inclusive")[int(fraction * 100) - 1])
