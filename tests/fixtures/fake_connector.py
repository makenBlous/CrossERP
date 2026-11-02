"""测试用 CSV 连接器。不解析真实平台。"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crosserp.connectors.base import SourceKind
from crosserp.core.enums import Platform
from crosserp.core.models import CanonicalRecord, ColumnMapping, OrderLineRec, RawRow

_ORDER_AT = datetime(2026, 10, 1, tzinfo=UTC)


class FakeCsvConnector:
    """读简单 CSV。bad=1 的行在 normalize 时失败。"""

    id = "fake.csv"
    kind: SourceKind = "orders"
    version = "0.1.0"
    fail_read = False

    def sniff(self, path: Path) -> float:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                header = handle.readline()
        except OSError:
            return 0.0
        names = {part.strip() for part in header.split(",")}
        if {"order_id", "sku", "qty", "price"} <= names:
            return 0.8
        return 0.0

    def read(self, path: Path, mapping: ColumnMapping | None = None) -> Iterator[RawRow]:
        del mapping
        if self.fail_read:
            raise OSError("模拟读失败")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row_no, payload in enumerate(reader, start=2):
                yield RawRow(
                    row_no=row_no,
                    payload=_string_payload(payload),
                    source_file=path.name,
                )

    def normalize(self, row: RawRow) -> list[CanonicalRecord]:
        if row.payload.get("bad") == "1":
            raise ValueError("故意坏行")
        missing = [
            name for name in ("order_id", "sku", "qty", "price") if not row.payload.get(name)
        ]
        if missing:
            raise ValueError(f"缺少列 {'、'.join(missing)}")
        record = OrderLineRec(
            platform=Platform.OTHER,
            marketplace="fake",
            store_name="测试店铺",
            store_currency="USD",
            platform_order_id=row.payload["order_id"],
            platform_sku=row.payload["sku"],
            qty=int(row.payload["qty"]),
            order_date=_ORDER_AT,
            item_price=Decimal(row.payload["price"]),
            currency="USD",
        )
        return [record]


def _string_payload(payload: dict[str, str | None]) -> dict[str, str]:
    rendered: dict[str, str] = {}
    for key, value in payload.items():
        if key is None:
            continue
        rendered[key] = "" if value is None else value
    return rendered
