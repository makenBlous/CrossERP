"""Human-readable XLSX profit report."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from openpyxl import Workbook  # type: ignore[import-untyped]
from openpyxl.styles import Font  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp import __version__
from crosserp.db.schema import Issue, ProfitSnapshot, Store
from crosserp.issues.catalog import definition, render

SKU_HEADERS = (
    "期间",
    "店铺",
    "内部SKU",
    "币种",
    "销量",
    "退款量",
    "收入",
    "促销",
    "平台费",
    "退款",
    "采购成本",
    "头程",
    "广告",
    "利润",
    "汇率",
    "人民币利润",
    "备注",
    "状态",
    "是否全部匹配",
)


def write_report_xlsx(
    session: Session, *, period: str, reports: Sequence[object], path: Path, overwrite: bool = False
) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在: {path}")
    workbook = Workbook()
    sku_sheet = workbook.active
    sku_sheet.title = "SKU利润"
    sku_sheet.append(SKU_HEADERS)
    for cell in sku_sheet[1]:
        cell.font = Font(bold=True)
    statement = (
        select(ProfitSnapshot, Store)
        .join(Store, Store.id == ProfitSnapshot.store_id)
        .where(ProfitSnapshot.period == period)
        .order_by(Store.name, ProfitSnapshot.internal_sku)
    )
    snapshots = list(session.execute(statement))
    for snapshot, store in snapshots:
        sku_sheet.append(
            [
                period,
                store.name,
                snapshot.internal_sku,
                snapshot.currency,
                snapshot.qty_sold,
                snapshot.qty_refunded,
                snapshot.revenue,
                snapshot.promotion,
                snapshot.fees,
                snapshot.refunds,
                snapshot.cogs,
                snapshot.freight,
                "n/a" if snapshot.ads is None else snapshot.ads,
                snapshot.profit,
                snapshot.fx_rate,
                snapshot.profit_cny,
                "未含广告",
                snapshot.status,
                "是" if snapshot.status == "ok" else "否",
            ]
        )
    for row in sku_sheet.iter_rows(min_row=2, min_col=7, max_col=16):
        for cell in row:
            if cell.value is not None and isinstance(cell.value, Decimal):
                cell.number_format = "#,##0.00"
    issue_sheet = workbook.create_sheet("异常清单")
    issue_sheet.append(
        (
            "原因码",
            "中文名",
            "严重度",
            "店铺",
            "订单号",
            "SKU",
            "中文说明",
            "建议动作",
            "来源文件+行号",
        )
    )
    for cell in issue_sheet[1]:
        cell.font = Font(bold=True)
    for issue in session.scalars(select(Issue).where(Issue.status == "open")):
        detail = issue.detail_json if isinstance(issue.detail_json, dict) else {}
        store_value = detail.get("store_id")
        try:
            issue_store = session.get(Store, UUID(str(store_value))) if store_value else None
        except ValueError:
            issue_store = None
        item = definition(issue.kind)
        issue_sheet.append(
            [
                issue.kind,
                item.name_zh,
                issue.severity,
                None if issue_store is None else issue_store.name,
                detail.get("order_id", ""),
                detail.get("sku", ""),
                render(issue),
                item.action_zh,
                f"{detail.get('source_file', '')}:{detail.get('row_no', '')}",
            ],
        )
    issue_sheet.auto_filter.ref = issue_sheet.dimensions
    note = workbook.create_sheet("说明")
    note.append(("项目", "值"))
    note.append(("生成时间 UTC", datetime.now(UTC).isoformat()))
    note.append(("CrossERP 版本", __version__))
    note.append(
        (
            "口径",
            "未含广告；退款不冲回成本；"  # noqa: RUF001
            "非订单费用未分摊；金额最后一步 ROUND_HALF_UP 到 2 位。",  # noqa: RUF001
        ),
    )
    note.append(("快照数", len(snapshots)))
    for sheet in workbook.worksheets:
        sheet.freeze_panes = "A2"
        sheet.column_dimensions["A"].width = 18
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
