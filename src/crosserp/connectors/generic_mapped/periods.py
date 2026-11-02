"""成本生效期。区间含开始。不含结束。结束为空表示未结束。"""

from __future__ import annotations

from datetime import UTC, datetime


def periods_overlap(
    left_from: datetime,
    left_to: datetime | None,
    right_from: datetime,
    right_to: datetime | None,
) -> bool:
    """两段生效期是否相交。结束时刻不含在区间内。"""
    left_ends_first = left_to is not None and left_to <= right_from
    right_ends_first = right_to is not None and right_to <= left_from
    return not left_ends_first and not right_ends_first


def segment_text(start: datetime, end: datetime | None) -> str:
    """把一段生效期写成 UTC 文本。"""
    start_text = start.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    if end is None:
        return f"{start_text} 起未结束"
    end_text = end.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"{start_text} 至 {end_text}"


def overlap_message(sku: str, left: str, right: str) -> str:
    """PARSE_ERROR 用的冲突说明。两段都写出来。"""
    return f"内部 SKU {sku} 生效期重叠。{left} 与 {right} 冲突。"
