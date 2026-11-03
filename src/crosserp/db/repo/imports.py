"""导入批次、原始行和标准记录的写入。调用方负责提交。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.core.enums import ImportStatus
from crosserp.db.schema import (
    Fee,
    FxRate,
    ImportBatch,
    Issue,
    OrderLine,
    RawRow,
    Settlement,
    SettlementLine,
    Sku,
    SkuCost,
    Store,
)


def get_successful_import_by_sha256(session: Session, file_sha256: str) -> ImportBatch | None:
    """按文件哈希读取最早的成功批次。失败和进行中的批次不算重复。"""
    statement = (
        select(ImportBatch)
        .where(
            ImportBatch.done_sha256 == file_sha256,
            ImportBatch.status == ImportStatus.DONE.value,
        )
        .order_by(ImportBatch.imported_at)
    )
    return session.scalars(statement).first()


def get_running_import_by_sha256(session: Session, file_sha256: str) -> ImportBatch | None:
    """读取同一文件仍在 running 的批次。"""
    statement = (
        select(ImportBatch)
        .where(
            ImportBatch.file_sha256 == file_sha256,
            ImportBatch.status == ImportStatus.RUNNING.value,
        )
        .order_by(ImportBatch.imported_at.desc())
    )
    return session.scalars(statement).first()


def get_latest_failed_import_by_sha256(session: Session, file_sha256: str) -> ImportBatch | None:
    """读取同一文件最近的失败批次, 用于建立重试关系。"""
    statement = (
        select(ImportBatch)
        .where(
            ImportBatch.file_sha256 == file_sha256,
            ImportBatch.status == ImportStatus.FAILED.value,
        )
        .order_by(ImportBatch.imported_at.desc())
    )
    return session.scalars(statement).first()


def insert_import_batch(
    session: Session,
    *,
    connector_id: str,
    connector_version: str,
    file_name: str,
    file_sha256: str | None,
    retry_of_batch_id: UUID | None = None,
    imported_at: datetime,
) -> ImportBatch:
    """新建 running 批次。row_count 与 error_count 从 0 开始。"""
    batch = ImportBatch(
        connector_id=connector_id,
        connector_version=connector_version,
        file_name=file_name,
        file_sha256=file_sha256,
        retry_of_batch_id=retry_of_batch_id,
        imported_at=imported_at,
        row_count=0,
        status=ImportStatus.RUNNING.value,
        error_count=0,
    )
    session.add(batch)
    session.flush()
    return batch


def mark_import_batch(
    session: Session,
    batch: ImportBatch,
    *,
    status: str,
    row_count: int,
    error_count: int,
    failure_code: str | None = None,
    failure_reason: str | None = None,
) -> None:
    """更新批次计数和状态。不提交。"""
    batch.status = status
    batch.row_count = row_count
    batch.error_count = error_count
    batch.done_sha256 = batch.file_sha256 if status == ImportStatus.DONE.value else None
    batch.failure_code = failure_code
    batch.failure_reason = failure_reason
    session.flush()


def mark_import_batch_failed(
    session: Session,
    batch: ImportBatch,
    *,
    failure_code: str,
    failure_reason: str,
) -> None:
    """人工把 running 批次标成失败。"""
    if batch.status != ImportStatus.RUNNING.value:
        raise ValueError(f"批次当前状态是 {batch.status}，只能标记 running 批次")  # noqa: RUF001
    mark_import_batch(
        session,
        batch,
        status=ImportStatus.FAILED.value,
        row_count=batch.row_count,
        error_count=batch.error_count,
        failure_code=failure_code,
        failure_reason=failure_reason,
    )


def insert_raw_row(
    session: Session,
    *,
    batch_id: UUID,
    row_no: int,
    payload: dict[str, str],
) -> RawRow:
    """原样写入 payload。不丢未知列。"""
    row = RawRow(batch_id=batch_id, row_no=row_no, payload_json=dict(payload))
    session.add(row)
    session.flush()
    return row


def insert_issue(
    session: Session,
    *,
    kind: str,
    severity: str,
    detail_json: dict[str, Any],
    status: str,
    created_at: datetime,
    settlement_line_id: UUID | None = None,
    order_line_id: UUID | None = None,
    recon_run_id: UUID | None = None,
) -> Issue:
    """写入一条异常。"""
    issue = Issue(
        kind=kind,
        severity=severity,
        settlement_line_id=settlement_line_id,
        order_line_id=order_line_id,
        recon_run_id=recon_run_id,
        detail_json=detail_json,
        status=status,
        resolution_note=None,
        created_at=created_at,
    )
    session.add(issue)
    session.flush()
    return issue


def ensure_store(
    session: Session,
    *,
    store_id: UUID | None,
    platform: str,
    marketplace: str,
    name: str,
    currency: str,
) -> UUID:
    """按主键或平台+站点+店名查找店铺。没有则创建。币种不一致则报错。"""
    if store_id is not None:
        found = session.get(Store, store_id)
        if found is None:
            raise ValueError(f"店铺不存在 {store_id}")
        return found.id
    statement = select(Store).where(
        Store.platform == platform,
        Store.marketplace == marketplace,
        Store.name == name,
    )
    existing = session.scalars(statement).one_or_none()
    if existing is not None:
        if existing.currency != currency:
            raise ValueError(
                f"店铺 {name} 已存在。币种是 {existing.currency}。与本行 {currency} 不一致。"
            )
        return existing.id
    created = Store(platform=platform, marketplace=marketplace, name=name, currency=currency)
    session.add(created)
    session.flush()
    return created.id


def get_settlement(session: Session, *, platform: str, external_id: str) -> Settlement | None:
    """按平台和外部单号读取结算头。"""
    statement = select(Settlement).where(
        Settlement.platform == platform,
        Settlement.external_id == external_id,
    )
    return session.scalars(statement).one_or_none()


def insert_settlement(
    session: Session,
    *,
    store_id: UUID,
    platform: str,
    external_id: str,
    period_start: datetime,
    period_end: datetime,
    deposit_date: datetime | None,
    total: Decimal,
    currency: str,
    source_batch_id: UUID,
) -> Settlement:
    """写入结算头。"""
    row = Settlement(
        store_id=store_id,
        platform=platform,
        external_id=external_id,
        period_start=period_start,
        period_end=period_end,
        deposit_date=deposit_date,
        total=total,
        currency=currency,
        source_batch_id=source_batch_id,
    )
    session.add(row)
    session.flush()
    return row


def insert_settlement_line(
    session: Session,
    *,
    settlement_id: UUID,
    transaction_type: str,
    order_id: str | None,
    order_item_code: str | None,
    sku: str | None,
    qty: int | None,
    amount_type: str | None,
    amount_description: str | None,
    amount: Decimal,
    posted_at: datetime | None,
    raw_row_id: int,
) -> SettlementLine:
    """写入结算明细。并指回原始行。"""
    row = SettlementLine(
        settlement_id=settlement_id,
        transaction_type=transaction_type,
        order_id=order_id,
        order_item_code=order_item_code,
        sku=sku,
        qty=qty,
        amount_type=amount_type,
        amount_description=amount_description,
        amount=amount,
        posted_at=posted_at,
        raw_row_id=raw_row_id,
    )
    session.add(row)
    session.flush()
    return row


def insert_fee(
    session: Session,
    *,
    settlement_line_id: UUID,
    fee_category: str,
    amount: Decimal,
) -> Fee:
    """写入已给出的费用分类。未给出时不调用。"""
    row = Fee(
        settlement_line_id=settlement_line_id,
        fee_category=fee_category,
        amount=amount,
    )
    session.add(row)
    session.flush()
    return row


def insert_order_line(
    session: Session,
    *,
    store_id: UUID,
    platform_order_id: str,
    order_item_id: str | None,
    platform_sku: str,
    qty: int,
    order_date: datetime,
    item_price: Decimal | None,
    currency: str,
    source_batch_id: UUID,
    raw_row_id: int,
) -> OrderLine:
    """写入订单行。并指回原始行。"""
    row = OrderLine(
        store_id=store_id,
        platform_order_id=platform_order_id,
        order_item_id=order_item_id,
        platform_sku=platform_sku,
        qty=qty,
        order_date=order_date,
        item_price=item_price,
        currency=currency,
        source_batch_id=source_batch_id,
        raw_row_id=raw_row_id,
    )
    session.add(row)
    session.flush()
    return row


def insert_sku(
    session: Session,
    *,
    store_id: UUID,
    platform_sku: str,
    internal_sku: str,
    title: str | None,
    active: bool,
) -> Sku:
    """写入平台 SKU 映射。"""
    row = Sku(
        store_id=store_id,
        platform_sku=platform_sku,
        internal_sku=internal_sku,
        title=title,
        active=active,
    )
    session.add(row)
    session.flush()
    return row


def insert_sku_cost(
    session: Session,
    *,
    internal_sku: str,
    valid_from: datetime,
    valid_to: datetime | None,
    unit_cost: Decimal,
    currency: str,
    freight_per_unit: Decimal,
    source_batch_id: UUID,
) -> SkuCost:
    """写入单位成本。"""
    row = SkuCost(
        internal_sku=internal_sku,
        valid_from=valid_from,
        valid_to=valid_to,
        unit_cost=unit_cost,
        currency=currency,
        freight_per_unit=freight_per_unit,
        source_batch_id=source_batch_id,
    )
    session.add(row)
    session.flush()
    return row


def insert_fx_rate(
    session: Session,
    *,
    period: str,
    from_ccy: str,
    to_ccy: str,
    rate: Decimal,
    source: str,
) -> FxRate:
    """写入月汇率。同月同币对冲突由调用方处理。"""
    row = FxRate(period=period, from_ccy=from_ccy, to_ccy=to_ccy, rate=rate, source=source)
    session.add(row)
    session.flush()
    return row
