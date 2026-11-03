"""CSV export used for exact machine comparison."""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import ProfitSnapshot, Store


def write_report_csv(session: Session, *, period: str, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "profit.csv"
    rows = session.execute(
        select(ProfitSnapshot, Store)
        .join(Store, Store.id == ProfitSnapshot.store_id)
        .where(ProfitSnapshot.period == period)
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            (
                "period",
                "store",
                "internal_sku",
                "currency",
                "qty_sold",
                "qty_refunded",
                "revenue",
                "platform_fees",
                "refunds",
                "cogs",
                "freight",
                "profit",
                "fx_rate",
                "profit_cny",
                "status",
            )
        )
        for snapshot, store in rows:
            writer.writerow(
                (
                    period,
                    store.name,
                    snapshot.internal_sku,
                    snapshot.currency,
                    snapshot.qty_sold,
                    snapshot.qty_refunded,
                    snapshot.revenue,
                    snapshot.fees,
                    snapshot.refunds,
                    snapshot.cogs,
                    snapshot.freight,
                    snapshot.profit,
                    snapshot.fx_rate,
                    snapshot.profit_cny,
                    snapshot.status,
                )
            )
