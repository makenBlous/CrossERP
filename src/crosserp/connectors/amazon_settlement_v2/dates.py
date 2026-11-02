"""Amazon 结算日期。全部转为 UTC。具体格式待真实数据验证。"""

from __future__ import annotations

import re
from datetime import UTC, datetime

# 待真实数据验证。合成样本只用前两种。任务另外点名了欧式日期和 ISO-8601。
_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_DATE_UTC = re.compile(r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2}) UTC$")
_DMY = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")
_ISO_OFFSET = re.compile(r"(?:Z|[+-]\d{2}:\d{2})$")


def parse_amazon_date(text: str) -> datetime | None:
    """解析 Amazon 结算日期。结果为 UTC。

    空字符串返回 None。无法识别则抛 ValueError。并保留原文。
    支持的写法待真实数据验证。不要据此反推平台一定会这样输出。

    - ``YYYY-MM-DD``
    - ``YYYY-MM-DD HH:MM:SS UTC``
    - ``DD.MM.YYYY``
    - 带时区的 ISO-8601。例如 ``2026-10-14T07:00:00Z``
    """
    if not isinstance(text, str):
        raise TypeError("日期文本必须是 str")
    original = text
    body = text.strip()
    if body == "":
        return None
    parsed = _parse_body(body, original)
    return parsed.astimezone(UTC)


def _parse_body(body: str, original: str) -> datetime:
    clock = _DATE_UTC.fullmatch(body)
    if clock is not None:
        return _build(original, clock.groups(), with_time=True)
    dmy = _DMY.fullmatch(body)
    if dmy is not None:
        day, month, year = dmy.groups()
        return _build(original, (year, month, day), with_time=False)
    date_only = _DATE.fullmatch(body)
    if date_only is not None:
        return _build(original, date_only.groups(), with_time=False)
    if "T" in body or _ISO_OFFSET.search(body) is not None:
        return _parse_iso(body, original)
    raise ValueError(f"无法解析日期 {original!r}")


def _build(original: str, parts: tuple[str, ...], *, with_time: bool) -> datetime:
    try:
        year, month, day = (int(part) for part in parts[:3])
        if with_time:
            hour, minute, second = (int(part) for part in parts[3:6])
            return datetime(year, month, day, hour, minute, second, tzinfo=UTC)
        return datetime(year, month, day, tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(f"无法解析日期 {original!r}") from exc


def _parse_iso(body: str, original: str) -> datetime:
    candidate = f"{body[:-1]}+00:00" if body.endswith("Z") else body
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError(f"无法解析日期 {original!r}") from exc
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise ValueError(f"无法解析日期 {original!r}")
    return parsed
