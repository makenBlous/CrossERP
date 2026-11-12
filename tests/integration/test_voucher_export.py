from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from openpyxl import load_workbook
from sqlalchemy import select

from crosserp.approval.payload import compute
from crosserp.approval.service import approve, create, submit
from crosserp.db.migrate import downgrade_base, upgrade_head
from crosserp.db.schema import Store, Voucher
from crosserp.db.session import session_scope
from crosserp.ledger.write_service import ApprovalRequired, export
from crosserp.vouchers.model import VoucherDraft, VoucherLineDraft
from crosserp.vouchers.service import save_draft

pytestmark = pytest.mark.db


def test_approved_voucher_exports_kingdee_xlsx_once(engine, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("crosserp.ledger.write_service.ledger_export_dir", lambda: tmp_path)
    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            store = Store(
                id=uuid4(),
                platform="shopify",
                marketplace="US",
                name="export-store",
                currency="USD",
            )
            session.add(store)
            session.flush()
            row = save_draft(
                session,
                VoucherDraft(
                    None,
                    store.id,
                    "2026-10",
                    "month",
                    "source-export",
                    "USD",
                    "a" * 64,
                    "b" * 64,
                    "operator",
                    (
                        VoucherLineDraft(
                            1,
                            "platform_receivable",
                            "1122",
                            "平台应收",
                            Decimal("10"),
                            Decimal("0"),
                            "销售",
                            "source",
                        ),
                        VoucherLineDraft(
                            2,
                            "sales_revenue",
                            "6001",
                            "主营业务收入",
                            Decimal("0"),
                            Decimal("10"),
                            "销售",
                            "source",
                        ),
                    ),
                ),
            )
            approval = create(
                session,
                target_type="voucher",
                target_id=str(row.id),
                requested_by="operator",
                payload_hash=compute(session, "voucher", str(row.id)),
            )
            submit(session, approval, actor="operator")
            token = approve(session, approval, approver="finance")
            batch = f"voucher:{row.id}"
        with session_scope(engine) as session:
            artifact = export(
                session,
                batch,
                "kingdee_xlsx",
                token,
            )
            output = Path(artifact.file_path or "")
            assert output.is_file()
            book = load_workbook(output, data_only=False)
            sheet = book["凭证"]
            headers = [cell.value for cell in sheet[1]]
            assert headers == [
                "凭证日期",
                "凭证字",
                "凭证号",
                "摘要",
                "科目编码",
                "科目名称",
                "借方金额",
                "贷方金额",
                "币别",
                "汇率",
                "原币金额",
            ]
            assert sheet.cell(2, 7).value == 10
            assert sheet.cell(3, 8).value == 10
        with session_scope(engine) as session:
            with pytest.raises(ApprovalRequired, match="已被使用"):
                export(
                    session,
                    batch,
                    "kingdee_xlsx",
                    token,
                )
            assert (
                session.scalar(select(Voucher).where(Voucher.source_id == "source-export"))
                is not None
            )
    finally:
        downgrade_base(url)
