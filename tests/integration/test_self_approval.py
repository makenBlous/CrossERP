import pytest

from crosserp.approval.service import SelfApprovalForbidden, approve, create, submit


def test_self_approval_requires_solo_mode(engine) -> None:
    from crosserp.db.migrate import downgrade_base, upgrade_head
    from crosserp.db.session import session_scope

    url = engine.url.render_as_string(hide_password=False)
    upgrade_head(url)
    try:
        with session_scope(engine) as session:
            row = create(session, target_type="issue", target_id="1", requested_by="maken")
            submit(session, row, actor="maken")
            with pytest.raises(SelfApprovalForbidden):
                approve(session, row, approver="maken", solo_mode=False)
            assert approve(session, row, approver="maken", solo_mode=True)
    finally:
        downgrade_base(url)
