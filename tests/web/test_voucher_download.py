from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import AuditLog, Store, Voucher
from crosserp.db.session import make_engine, session_scope
from crosserp.web.app import create_app


def test_unapproved_voucher_download_is_403_and_audited(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'voucher-web.sqlite'}"
    app = create_app(url)
    engine = make_engine(url)
    voucher_id = uuid4()
    with session_scope(engine) as session:
        create_user(session, username="finance", password="A-password-long", roles=(Role.FINANCE,))
        store = Store(id=uuid4(), platform="shopify", marketplace="US", name="web", currency="USD")
        session.add(store)
        session.flush()
        session.add(
            Voucher(
                id=voucher_id,
                store_id=store.id,
                period="2026-10",
                source_type="month",
                source_id="web",
                state="draft",
                currency="USD",
                total_debit=Decimal("1"),
                total_credit=Decimal("1"),
                inputs_hash="a" * 64,
                accounts_hash="b" * 64,
                created_by="operator",
                created_at=datetime.now(UTC),
            )
        )
    engine.dispose()
    client = TestClient(app)
    login = client.get("/login")
    response = client.post(
        "/login",
        data={
            "username": "finance",
            "password": "A-password-long",
            "csrf_token": login.cookies.get("crosserp_login_csrf"),
        },
    )
    assert response.status_code == 200
    denied = client.get(f"/vouchers/{voucher_id}/download?target=generic_xlsx")
    assert denied.status_code == 403
    engine = make_engine(url)
    with session_scope(engine) as session:
        assert (
            session.scalar(select(AuditLog).where(AuditLog.action == "ledger.export_denied"))
            is not None
        )
    engine.dispose()
