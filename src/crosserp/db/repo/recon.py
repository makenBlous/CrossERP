"""对账运行和匹配结果的数据库写入。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from crosserp.db.schema import Match, ReconRun


def create_recon_run(
    session: Session,
    *,
    store_id: UUID,
    period: str,
    as_of: date,
    rule_set_version: str,
    started_at: datetime,
) -> ReconRun:
    run = ReconRun(
        id=uuid4(),
        store_id=store_id,
        period=period,
        as_of=as_of,
        rule_set_version=rule_set_version,
        started_at=started_at,
        finished_at=None,
        status="running",
        groups_total=0,
        groups_matched=0,
        non_order_lines=0,
        created_by=None,
    )
    session.add(run)
    session.flush()
    return run


def finish_recon_run(
    session: Session,
    run: ReconRun,
    *,
    finished_at: datetime,
    groups_total: int,
    groups_matched: int,
    non_order_lines: int,
    status: str = "done",
) -> None:
    run.finished_at = finished_at
    run.groups_total = groups_total
    run.groups_matched = groups_matched
    run.non_order_lines = non_order_lines
    run.status = status
    session.flush()


def insert_match(
    session: Session,
    *,
    recon_run_id: UUID,
    settlement_line_id: UUID,
    order_line_id: UUID,
    rule_id: str,
    diff: Decimal,
    matched_at: datetime,
) -> Match:
    row = Match(
        recon_run_id=recon_run_id,
        settlement_line_id=settlement_line_id,
        order_line_id=order_line_id,
        rule_id=rule_id,
        status="matched",
        diff=diff,
        matched_at=matched_at,
    )
    session.add(row)
    session.flush()
    return row
