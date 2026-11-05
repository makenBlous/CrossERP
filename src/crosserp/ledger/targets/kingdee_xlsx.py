"""金蝶凭证 Excel 写出目标。模板字段可配置, 当前列名待真实模板验证。"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml  # type: ignore[import-untyped]
from openpyxl import Workbook  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import Store, Voucher, VoucherLine

_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "kingdee_voucher.yaml"


class KingdeeXlsxTarget:
    id = "kingdee_xlsx"
    supported_types = frozenset({"voucher"})

    def render(
        self,
        session: Session,
        *,
        batch_id: str,
        approval_id: str,
        output_dir: Path,
    ) -> Path:
        target_type, separator, voucher_text = batch_id.partition(":")
        if target_type != "voucher" or not separator:
            raise ValueError("kingdee_xlsx 目标只支持 voucher:<凭证 UUID>")
        voucher = session.get(Voucher, UUID(voucher_text))
        if voucher is None:
            raise LookupError(f"凭证不存在: {voucher_text}")
        store = session.get(Store, voucher.store_id)
        if store is None:
            raise LookupError(f"店铺不存在: {voucher.store_id}")
        lines = list(
            session.scalars(
                select(VoucherLine)
                .where(VoucherLine.voucher_id == voucher.id)
                .order_by(VoucherLine.line_no)
            )
        )
        config = _load_template()
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_store = "".join(char if char.isalnum() or char in "-_" else "_" for char in store.name)
        path = output_dir / f"voucher_{safe_store}_{voucher.period}_{approval_id[:8]}.xlsx"
        if path.exists():
            raise FileExistsError(f"输出文件已存在: {path}")
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = str(config["sheet"])
        columns = config["columns"]
        assert isinstance(columns, list)
        for column_no, column in enumerate(columns, start=1):
            assert isinstance(column, dict)
            sheet.cell(1, column_no, str(column["title"]))
        for row_no, line in enumerate(lines, start=2):
            values = _values(config, voucher, line, approval_id)
            for column_no, column in enumerate(columns, start=1):
                assert isinstance(column, dict)
                key = str(column["key"])
                cell = sheet.cell(row_no, column_no, values[key])
                if key in {"debit", "credit", "original_amount"}:
                    cell.number_format = str(config["amount_format"])
        total_row = len(lines) + 2
        sheet.cell(total_row, 1, "合计")
        for column_no, column in enumerate(columns, start=1):
            assert isinstance(column, dict)
            key = str(column["key"])
            if key == "debit":
                sheet.cell(total_row, column_no, voucher.total_debit).number_format = str(
                    config["amount_format"]
                )
            elif key == "credit":
                sheet.cell(total_row, column_no, voucher.total_credit).number_format = str(
                    config["amount_format"]
                )
        workbook.save(path)
        return path


def _load_template() -> dict[str, Any]:
    raw = yaml.safe_load(_TEMPLATE.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("columns"), list):
        raise ValueError("金蝶模板必须包含 columns")
    return raw


def _values(
    config: dict[str, Any], voucher: Voucher, line: VoucherLine, approval_id: str
) -> dict[str, object]:
    first_day = date.fromisoformat(f"{voucher.period}-01")
    return {
        "voucher_date": first_day,
        "voucher_word": str(config["voucher_word"]),
        "voucher_no": approval_id[:8],
        "summary": line.summary,
        "account_code": line.account_code,
        "account_name": line.account_name,
        "debit": line.debit,
        "credit": line.credit,
        "currency": voucher.currency,
        "exchange_rate": 1,
        "original_amount": line.debit if line.debit else line.credit,
    }
