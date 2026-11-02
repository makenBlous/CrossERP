"""导入一批文件。重复哈希拒绝。坏行记 PARSE_ERROR 后继续。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, assert_never
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crosserp.audit.log import append
from crosserp.connectors.base import FileConnector
from crosserp.connectors.generic_mapped.periods import (
    overlap_message,
    periods_overlap,
    segment_text,
)
from crosserp.core.enums import ImportStatus, IssueKind, IssueStatus
from crosserp.core.errors import DuplicateImportError, FileUnreadableError, RowParseError
from crosserp.core.models import (
    CanonicalRecord,
    ColumnMapping,
    FxRateRec,
    IssueRec,
    OrderLineRec,
    Provenance,
    RawRow,
    SettlementHeader,
    SettlementLineRec,
    SkuCostRec,
    SkuRec,
)
from crosserp.db.repo.fx import get_fx_rate, upsert_fx_rate
from crosserp.db.repo.imports import (
    ensure_store,
    get_import_batch_by_sha256,
    get_settlement,
    insert_fee,
    insert_import_batch,
    insert_issue,
    insert_order_line,
    insert_raw_row,
    insert_settlement,
    insert_settlement_line,
    insert_sku,
    insert_sku_cost,
    mark_import_batch,
)
from crosserp.db.schema import ImportBatch, SkuCost

_CHUNK = 1024 * 1024


@dataclass(frozen=True)
class ImportResult:
    """一次导入的结果。失败批次也返回。调用方提交后能看到 status=failed。"""

    batch_id: UUID
    file_sha256: str
    row_count: int
    error_count: int
    status: ImportStatus
    message: str | None = None


class _BatchAbort(Exception):
    """整批失败。数据行回滚后把批次标为 failed。"""


def import_file(
    session: Session,
    path: Path,
    connector: FileConnector,
    mapping: ColumnMapping | None = None,
) -> ImportResult:
    """导入一个文件。调用方提交事务。审计与批次在同一事务。"""
    digest = _file_sha256(path)
    _reject_duplicate(session, digest)
    file_name = _file_name(path)
    try:
        with session.begin_nested():
            batch = insert_import_batch(
                session,
                connector_id=connector.id,
                connector_version=connector.version,
                file_name=file_name,
                file_sha256=digest,
                imported_at=datetime.now(UTC),
            )
    except IntegrityError as exc:
        _reject_duplicate(session, digest)
        raise DuplicateImportError(digest, "未知", ImportStatus.FAILED.value) from exc

    try:
        with session.begin_nested():
            row_count, error_count = _consume(session, path, connector, mapping, batch)
    except Exception as exc:
        message = f"整批导入失败。{exc}"
        mark_import_batch(
            session,
            batch,
            status=ImportStatus.FAILED.value,
            row_count=0,
            error_count=0,
        )
        _write_audit(session, batch, message=message, mapping=mapping)
        return ImportResult(
            batch_id=batch.id,
            file_sha256=digest,
            row_count=0,
            error_count=0,
            status=ImportStatus.FAILED,
            message=message,
        )

    mark_import_batch(
        session,
        batch,
        status=ImportStatus.DONE.value,
        row_count=row_count,
        error_count=error_count,
    )
    _write_audit(session, batch, message=None, mapping=mapping)
    return ImportResult(
        batch_id=batch.id,
        file_sha256=digest,
        row_count=row_count,
        error_count=error_count,
        status=ImportStatus.DONE,
    )


def _consume(
    session: Session,
    path: Path,
    connector: FileConnector,
    mapping: ColumnMapping | None,
    batch: ImportBatch,
) -> tuple[int, int]:
    try:
        iterator = iter(connector.read(path, mapping))
    except Exception as exc:
        raise _BatchAbort(f"无法读取文件 {path.name}。{exc}") from exc
    row_count = 0
    error_count = 0
    try:
        while True:
            try:
                raw = next(iterator)
            except StopIteration:
                break
            except RowParseError as exc:
                row_count += 1
                if isinstance(exc.raw, dict):
                    insert_raw_row(
                        session,
                        batch_id=batch.id,
                        row_no=exc.row_no,
                        payload=exc.raw,
                    )
                error_count += _write_row_error(session, exc.row_no, str(exc), exc.raw)
                continue
            except Exception as exc:
                raise _BatchAbort(f"无法读取文件 {path.name}。{exc}") from exc
            row_count += 1
            stored = insert_raw_row(
                session,
                batch_id=batch.id,
                row_no=raw.row_no,
                payload=raw.payload,
            )
            try:
                records = list(connector.normalize(raw))
            except Exception as exc:
                error_count += _write_row_error(
                    session,
                    raw.row_no,
                    f"第 {raw.row_no} 行解析失败。{exc}",
                    raw.payload,
                )
                continue
            for record in records:
                filled = record.model_copy(
                    update={"provenance": _provenance(connector, batch.id, raw, path, mapping)}
                )
                try:
                    _persist(session, filled, batch.id, stored.id)
                except RowParseError as exc:
                    error_count += _write_row_error(
                        session,
                        exc.row_no,
                        str(exc),
                        exc.raw if isinstance(exc.raw, dict) else raw.payload,
                    )
                    continue
                if isinstance(filled, IssueRec) and filled.issue_kind is IssueKind.PARSE_ERROR:
                    error_count += 1
    finally:
        close = getattr(iterator, "close", None)
        if callable(close):
            close()
    return row_count, error_count


def _write_row_error(
    session: Session,
    row_no: int,
    message: str,
    raw: dict[str, str] | str | None,
) -> int:
    insert_issue(
        session,
        kind=IssueKind.PARSE_ERROR.value,
        severity="error",
        detail_json={"row_no": row_no, "error": message, "raw": raw},
        status=IssueStatus.OPEN.value,
        created_at=datetime.now(UTC),
    )
    return 1


def _persist(session: Session, record: CanonicalRecord, batch_id: UUID, raw_row_id: int) -> None:
    if isinstance(record, SettlementHeader):
        _write_header(session, record, batch_id)
        return
    if isinstance(record, SettlementLineRec):
        _write_line(session, record, raw_row_id)
        return
    if isinstance(record, OrderLineRec):
        _write_order(session, record, batch_id, raw_row_id)
        return
    if isinstance(record, SkuCostRec):
        _write_cost(session, record, batch_id)
        return
    if isinstance(record, FxRateRec):
        _write_fx(session, record)
        return
    if isinstance(record, SkuRec):
        _write_sku(session, record)
        return
    if isinstance(record, IssueRec):
        detail = dict(record.detail_json)
        if record.provenance is not None:
            detail.setdefault("row_no", record.provenance.row_no)
            detail.setdefault("source_file", record.provenance.source_file)
        insert_issue(
            session,
            kind=record.issue_kind.value,
            severity=record.severity,
            detail_json=detail,
            status=record.status.value,
            created_at=datetime.now(UTC),
        )
        return
    assert_never(record)


def _write_header(session: Session, record: SettlementHeader, batch_id: UUID) -> None:
    store_id = ensure_store(
        session,
        store_id=record.store_id,
        platform=record.platform.value,
        marketplace=record.marketplace,
        name=record.store_name,
        currency=record.currency,
    )
    insert_settlement(
        session,
        store_id=store_id,
        platform=record.platform.value,
        external_id=record.external_id,
        period_start=record.period_start,
        period_end=record.period_end,
        deposit_date=record.deposit_date,
        total=record.total,
        currency=record.currency,
        source_batch_id=batch_id,
    )


def _write_line(session: Session, record: SettlementLineRec, raw_row_id: int) -> None:
    settlement = get_settlement(
        session,
        platform=record.platform.value,
        external_id=record.external_id,
    )
    if settlement is None:
        raise _BatchAbort(f"结算明细缺少结算头 {record.external_id}")
    line = insert_settlement_line(
        session,
        settlement_id=settlement.id,
        transaction_type=record.transaction_type,
        order_id=record.order_id,
        order_item_code=record.order_item_code,
        sku=record.sku,
        qty=record.qty,
        amount_type=record.amount_type,
        amount_description=record.amount_description,
        amount=record.amount,
        posted_at=record.posted_at,
        raw_row_id=raw_row_id,
    )
    if record.fee_category is not None:
        insert_fee(
            session,
            settlement_line_id=line.id,
            fee_category=record.fee_category.value,
            amount=record.amount,
        )


def _write_cost(session: Session, record: SkuCostRec, batch_id: UUID) -> None:
    """写入成本。与已有生效期相交则整行 PARSE_ERROR。不插入。"""
    statement = select(SkuCost).where(SkuCost.internal_sku == record.internal_sku)
    for existing in session.scalars(statement):
        if not periods_overlap(
            record.valid_from, record.valid_to, existing.valid_from, existing.valid_to
        ):
            continue
        row_no = 1 if record.provenance is None else record.provenance.row_no
        message = overlap_message(
            record.internal_sku,
            f"本行 {segment_text(record.valid_from, record.valid_to)}",
            f"已有记录 {segment_text(existing.valid_from, existing.valid_to)}",
        )
        raise RowParseError(row_no, message)
    insert_sku_cost(
        session,
        internal_sku=record.internal_sku,
        valid_from=record.valid_from,
        valid_to=record.valid_to,
        unit_cost=record.unit_cost,
        currency=record.currency,
        freight_per_unit=record.freight_per_unit,
        source_batch_id=batch_id,
    )


def _write_fx(session: Session, record: FxRateRec) -> None:
    """同月同币对覆盖。覆盖时另写一条审计。"""
    existing = get_fx_rate(session, record.period, record.from_ccy, record.to_ccy)
    rate_id = uuid4() if existing is None else existing.id
    before = None
    if existing is not None:
        before = {
            "period": existing.period,
            "from_ccy": existing.from_ccy,
            "to_ccy": existing.to_ccy,
            "rate": existing.rate,
            "source": existing.source,
        }
    upsert_fx_rate(
        session,
        rate_id=rate_id,
        period=record.period,
        from_ccy=record.from_ccy,
        to_ccy=record.to_ccy,
        rate=record.rate,
        source=record.source,
    )
    if before is None:
        return
    after: dict[str, Any] = {
        "period": record.period,
        "from_ccy": record.from_ccy,
        "to_ccy": record.to_ccy,
        "rate": record.rate,
        "source": record.source,
    }
    if record.provenance is not None:
        after["row_no"] = record.provenance.row_no
        after["source_file"] = record.provenance.source_file
    append(
        session,
        actor_type="system",
        action="fx_rate_upsert",
        target_type="fx_rate",
        target_id=str(rate_id),
        before=before,
        after=after,
        reason="同月同币对覆盖",
        self_approved=False,
    )


def _write_sku(session: Session, record: SkuRec) -> None:
    store_id = ensure_store(
        session,
        store_id=record.store_id,
        platform=record.platform.value,
        marketplace=record.marketplace,
        name=record.store_name,
        currency=record.store_currency,
    )
    insert_sku(
        session,
        store_id=store_id,
        platform_sku=record.platform_sku,
        internal_sku=record.internal_sku,
        title=record.title,
        active=record.active,
    )


def _write_order(session: Session, record: OrderLineRec, batch_id: UUID, raw_row_id: int) -> None:
    store_id = ensure_store(
        session,
        store_id=record.store_id,
        platform=record.platform.value,
        marketplace=record.marketplace,
        name=record.store_name,
        currency=record.store_currency,
    )
    insert_order_line(
        session,
        store_id=store_id,
        platform_order_id=record.platform_order_id,
        order_item_id=record.order_item_id,
        platform_sku=record.platform_sku,
        qty=record.qty,
        order_date=record.order_date,
        item_price=record.item_price,
        currency=record.currency,
        source_batch_id=batch_id,
        raw_row_id=raw_row_id,
    )


def _provenance(
    connector: FileConnector,
    batch_id: UUID,
    raw: RawRow,
    path: Path,
    mapping: ColumnMapping | None,
) -> Provenance:
    source_name = None if mapping is None else mapping.source_name
    return Provenance(
        connector_id=connector.id,
        connector_version=connector.version,
        import_batch_id=batch_id,
        source_file=str(path),
        row_no=raw.row_no,
        source_name=source_name,
    )


def _write_audit(
    session: Session,
    batch: ImportBatch,
    *,
    message: str | None,
    mapping: ColumnMapping | None,
) -> None:
    after: dict[str, Any] = {
        "connector_id": batch.connector_id,
        "connector_version": batch.connector_version,
        "file_name": batch.file_name,
        "file_sha256": batch.file_sha256,
        "row_count": batch.row_count,
        "error_count": batch.error_count,
        "status": batch.status,
    }
    if mapping is not None and mapping.source_name:
        after["source_name"] = mapping.source_name
    if message is not None:
        after["message"] = message
    append(
        session,
        actor_type="system",
        action="import",
        target_type="import_batch",
        target_id=str(batch.id),
        before=None,
        after=after,
        reason="导入文件" if message is None else "导入失败",
        self_approved=False,
    )


def _reject_duplicate(session: Session, digest: str) -> None:
    existing = get_import_batch_by_sha256(session, digest)
    if existing is None:
        return
    raise DuplicateImportError(digest, _format_time(existing.imported_at), existing.status)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(_CHUNK)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise FileUnreadableError(f"无法读取文件 {path.name}。{exc}") from exc
    return digest.hexdigest()


def _file_name(path: Path) -> str:
    name = path.name
    if len(name) > 512:
        raise FileUnreadableError(f"文件名超过 512 个字符。{name[:32]}...")
    if not name:
        raise FileUnreadableError("文件名为空。无法导入。")
    return name


def _format_time(value: datetime) -> str:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
