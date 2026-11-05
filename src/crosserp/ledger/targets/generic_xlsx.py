"""通用凭证 Excel 目标。"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from openpyxl import Workbook  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import Store, Voucher, VoucherLine


class GenericXlsxTarget:
    id = "generic_xlsx"
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
            raise ValueError("generic_xlsx 目标只支持 voucher:<凭证 UUID>")
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
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_store = "".join(char if char.isalnum() or char in "-_" else "_" for char in store.name)
        path = output_dir / f"voucher_{safe_store}_{voucher.period}_{approval_id[:8]}-generic.xlsx"
        if path.exists():
            raise FileExistsError(f"输出文件已存在: {path}")
        workbook = Workbook()
        header = workbook.active
        header.title = "凭证头"
        header.append(["凭证 ID", "期间", "店铺", "币别", "借方合计", "贷方合计"])
        header.append(
            [
                str(voucher.id),
                voucher.period,
                store.name,
                voucher.currency,
                voucher.total_debit,
                voucher.total_credit,
            ]
        )
        header.cell(2, 5).number_format = "0.00"
        header.cell(2, 6).number_format = "0.00"
        detail = workbook.create_sheet("分录")
        detail.append(["行号", "科目编码", "科目名称", "摘要", "借方", "贷方", "来源"])
        for line in lines:
            detail.append(
                [
                    line.line_no,
                    line.account_code,
                    line.account_name,
                    line.summary,
                    line.debit,
                    line.credit,
                    line.source_ref,
                ]
            )
            detail.cell(detail.max_row, 5).number_format = "0.00"
            detail.cell(detail.max_row, 6).number_format = "0.00"
        workbook.save(path)
        return path
