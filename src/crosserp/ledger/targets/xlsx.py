"""期间利润报表 XLSX 写出目标。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from crosserp.profit.report_xlsx import write_report_xlsx


class XlsxLedgerTarget:
    """复用 T22 报表格式，文件已存在时不覆盖。"""  # noqa: RUF002

    id = "xlsx"

    def render(
        self,
        session: Session,
        *,
        batch_id: str,
        approval_id: str,
        output_dir: Path,
    ) -> Path:
        target_type, separator, target_id = batch_id.partition(":")
        if target_type != "profit_report" or not separator:
            raise ValueError("xlsx 目标只支持 profit_report:<店铺>:<期间>")
        store_name, separator, period = target_id.rpartition(":")
        if not separator or not store_name or len(period) != 7:
            raise ValueError("利润报表对象必须是 profit_report:<店铺>:YYYY-MM")
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"profit-report-{approval_id}.xlsx"
        if path.exists():
            raise FileExistsError(f"输出文件已存在: {path}")
        write_report_xlsx(session, period=period, reports=(), path=path, store_name=store_name)
        return path
