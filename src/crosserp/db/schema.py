"""v0.1 业务表。字段按实施方案第 4 节。不建 v0.5 表。

金额列用 Money4。汇率用 FxRate。时间用 UtcDateTime。JSON 用 JSON。
分类字段用 String(32)。不用数据库原生 ENUM。要建索引的字符串长度不超过 255。
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from crosserp.db.types import FxRate as FxRateColumn
from crosserp.db.types import Money4, UtcDateTime

_NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# 分类字段统一 32。原因码最长的 SETTLEMENT_UNBALANCED 也放得下。
_KIND = String(32)


class Base(DeclarativeBase):
    """v0.1 声明式基类。"""

    metadata = MetaData(naming_convention=_NAMING)


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)


class ImportBatch(Base):
    """一次文件导入。只有成功批次才按 sha256 拒绝重复。失败批次可以重导。"""

    __tablename__ = "import_batch"
    __table_args__ = (Index("ix_import_batch_file_sha256", "file_sha256"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    connector_id: Mapped[str] = mapped_column(String(64))
    connector_version: Mapped[str] = mapped_column(String(32))
    file_name: Mapped[str] = mapped_column(String(512))
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    done_sha256: Mapped[str | None] = mapped_column(String(64), unique=True)
    retry_of_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("import_batch.id")
    )
    failure_code: Mapped[str | None] = mapped_column(String(32))
    failure_reason: Mapped[str | None] = mapped_column(String(1000))
    imported_at: Mapped[datetime] = mapped_column(UtcDateTime())
    row_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(_KIND)
    error_count: Mapped[int] = mapped_column(Integer)


class RawRow(Base):
    """原始行。主键用自增 BigInteger。数量大。推断不用 Uuid。

    SQLite 只有 INTEGER PRIMARY KEY 会自增。因此这一列在 SQLite 上用 Integer。
    MySQL 与 PostgreSQL 仍是 BIGINT。
    """

    __tablename__ = "raw_row"
    __table_args__ = (Index("ix_raw_row_batch_id", "batch_id"),)

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("import_batch.id"))
    row_no: Mapped[int] = mapped_column(Integer)
    payload_json: Mapped[Any] = mapped_column(JSON())


class Store(Base):
    """店铺。"""

    __tablename__ = "store"

    id: Mapped[uuid.UUID] = _uuid_pk()
    platform: Mapped[str] = mapped_column(_KIND)
    marketplace: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    currency: Mapped[str] = mapped_column(String(3))


class Sku(Base):
    """平台 SKU 与内部 SKU 的映射。"""

    __tablename__ = "sku"
    __table_args__ = (
        UniqueConstraint("store_id", "platform_sku", name="uq_sku_store_platform_sku"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("store.id"))
    platform_sku: Mapped[str] = mapped_column(String(128))
    internal_sku: Mapped[str] = mapped_column(String(128))
    title: Mapped[str | None] = mapped_column(String(512))
    active: Mapped[bool] = mapped_column(Boolean())


class SkuCost(Base):
    """按生效期存放的单位成本。取订单日期落在区间内的那条。"""

    __tablename__ = "sku_cost"
    __table_args__ = (
        Index("ix_sku_cost_internal_sku", "internal_sku"),
        Index("ix_sku_cost_source_batch_id", "source_batch_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    internal_sku: Mapped[str] = mapped_column(String(128))
    valid_from: Mapped[datetime] = mapped_column(UtcDateTime())
    valid_to: Mapped[datetime | None] = mapped_column(UtcDateTime())
    unit_cost: Mapped[Decimal] = mapped_column(Money4())
    currency: Mapped[str] = mapped_column(String(3))
    freight_per_unit: Mapped[Decimal] = mapped_column(Money4())
    # 手工成本可以没有导入批次。推断。
    source_batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("import_batch.id"))


class FxRate(Base):
    """用户填写的月汇率。v0.x 不调实时汇率。"""

    __tablename__ = "fx_rate"
    __table_args__ = (
        UniqueConstraint("period", "from_ccy", "to_ccy", name="uq_fx_rate_period_ccy"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[str] = mapped_column(String(7))
    from_ccy: Mapped[str] = mapped_column(String(3))
    to_ccy: Mapped[str] = mapped_column(String(3))
    rate: Mapped[Decimal] = mapped_column(FxRateColumn())
    source: Mapped[str] = mapped_column(String(128))


class OrderLine(Base):
    """订单行。来自领星、赛狐或 Shopify 订单。"""

    __tablename__ = "order_line"
    __table_args__ = (
        Index("ix_order_line_store_id", "store_id"),
        Index("ix_order_line_platform_order_id", "platform_order_id"),
        Index("ix_order_line_source_batch_id", "source_batch_id"),
        Index("ix_order_line_raw_row_id", "raw_row_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("store.id"))
    platform_order_id: Mapped[str] = mapped_column(String(64))
    order_item_id: Mapped[str | None] = mapped_column(String(64))
    platform_sku: Mapped[str] = mapped_column(String(128))
    qty: Mapped[int] = mapped_column(Integer)
    order_date: Mapped[datetime] = mapped_column(UtcDateTime())
    # 实施方案 6.2 允许为空。空则不做金额比对。
    item_price: Mapped[Decimal | None] = mapped_column(Money4())
    currency: Mapped[str] = mapped_column(String(3))
    source_batch_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("import_batch.id"))
    raw_row_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("raw_row.id"))


class Settlement(Base):
    """一次结算或一次打款。"""

    __tablename__ = "settlement"
    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uq_settlement_platform_external_id"),
        Index("ix_settlement_store_id", "store_id"),
        Index("ix_settlement_source_batch_id", "source_batch_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("store.id"))
    platform: Mapped[str] = mapped_column(_KIND)
    external_id: Mapped[str] = mapped_column(String(64))
    period_start: Mapped[datetime] = mapped_column(UtcDateTime())
    period_end: Mapped[datetime] = mapped_column(UtcDateTime())
    # 打款前 deposit-date 可能为空。推断。
    deposit_date: Mapped[datetime | None] = mapped_column(UtcDateTime())
    total: Mapped[Decimal] = mapped_column(Money4())
    currency: Mapped[str] = mapped_column(String(3))
    source_batch_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("import_batch.id"))


class SettlementLine(Base):
    """结算明细。Amazon 一行一个费用项。Shopify 一行一笔交易。"""

    __tablename__ = "settlement_line"
    __table_args__ = (
        Index("ix_settlement_line_settlement_id", "settlement_id"),
        Index("ix_settlement_line_raw_row_id", "raw_row_id"),
        # order_id 64 + sku 128。utf8mb4 下联合索引不超过 3072 字节。
        Index("ix_settlement_line_order_sku", "order_id", "sku"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    settlement_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("settlement.id"))
    transaction_type: Mapped[str] = mapped_column(String(64))
    order_id: Mapped[str | None] = mapped_column(String(64))
    order_item_code: Mapped[str | None] = mapped_column(String(64))
    sku: Mapped[str | None] = mapped_column(String(128))
    qty: Mapped[int | None] = mapped_column(Integer)
    amount_type: Mapped[str | None] = mapped_column(String(64))
    amount_description: Mapped[str | None] = mapped_column(String(512))
    amount: Mapped[Decimal] = mapped_column(Money4())
    posted_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    raw_row_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("raw_row.id"))


class Fee(Base):
    """由 amount-type 与 amount-description 映射后的费用。"""

    __tablename__ = "fee"
    __table_args__ = (Index("ix_fee_settlement_line_id", "settlement_line_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    settlement_line_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("settlement_line.id"))
    fee_category: Mapped[str] = mapped_column(_KIND)
    amount: Mapped[Decimal] = mapped_column(Money4())


class ReconRun(Base):
    """一次确定性对账运行。重跑保留旧运行, 最新 done 运行是当前结果。"""

    __tablename__ = "recon_run"
    __table_args__ = (Index("ix_recon_run_store_period", "store_id", "period"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("store.id"))
    period: Mapped[str] = mapped_column(String(7))
    as_of: Mapped[date] = mapped_column(Date())
    rule_set_version: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(UtcDateTime())
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    status: Mapped[str] = mapped_column(_KIND)
    groups_total: Mapped[int] = mapped_column(Integer)
    groups_matched: Mapped[int] = mapped_column(Integer)
    non_order_lines: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[str | None] = mapped_column(String(64))


class Match(Base):
    """一条匹配结果。settlement_line_id 可空。表示组级匹配。推断。未另建组表。"""

    __tablename__ = "match"
    __table_args__ = (
        Index("ix_match_settlement_line_id", "settlement_line_id"),
        Index("ix_match_order_line_id", "order_line_id"),
        Index("ix_match_recon_run_id", "recon_run_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    recon_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("recon_run.id"))
    settlement_line_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("settlement_line.id")
    )
    order_line_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("order_line.id"))
    rule_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(_KIND)
    diff: Mapped[Decimal] = mapped_column(Money4())
    matched_at: Mapped[datetime] = mapped_column(UtcDateTime())


class Issue(Base):
    """未匹配或解析失败必须有一条异常。"""

    __tablename__ = "issue"
    __table_args__ = (
        Index("ix_issue_settlement_line_id", "settlement_line_id"),
        Index("ix_issue_order_line_id", "order_line_id"),
        Index("ix_issue_recon_run_id", "recon_run_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    recon_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("recon_run.id"))
    kind: Mapped[str] = mapped_column(_KIND)
    severity: Mapped[str] = mapped_column(_KIND)
    settlement_line_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("settlement_line.id")
    )
    order_line_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("order_line.id"))
    detail_json: Mapped[Any] = mapped_column(JSON())
    status: Mapped[str] = mapped_column(_KIND)
    resolution_note: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class ProfitSnapshot(Base):
    """可复算的利润结果。ads 为空表示本期未含广告。"""

    __tablename__ = "profit_snapshot"
    __table_args__ = (Index("ix_profit_snapshot_store_id", "store_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[str] = mapped_column(String(7))
    internal_sku: Mapped[str] = mapped_column(String(128))
    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("store.id"))
    revenue: Mapped[Decimal] = mapped_column(Money4())
    fees: Mapped[Decimal] = mapped_column(Money4())
    refunds: Mapped[Decimal] = mapped_column(Money4())
    cogs: Mapped[Decimal] = mapped_column(Money4())
    freight: Mapped[Decimal] = mapped_column(Money4())
    ads: Mapped[Decimal | None] = mapped_column(Money4())
    profit: Mapped[Decimal] = mapped_column(Money4())
    currency: Mapped[str] = mapped_column(String(3))
    calc_version: Mapped[str] = mapped_column(String(32))
    inputs_hash: Mapped[str] = mapped_column(String(64))


class AuditLog(Base):
    """业务审计。只追加。approval 与 app_user 是 v0.5 表。这里不做外键。

    seq 从 1 递增。应用分配。不用数据库自增。三库行为一致。
    """

    __tablename__ = "audit_log"
    __table_args__ = (UniqueConstraint("seq", name="uq_audit_log_seq"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    seq: Mapped[int] = mapped_column(Integer)
    ts: Mapped[datetime] = mapped_column(UtcDateTime())
    actor_type: Mapped[str] = mapped_column(_KIND)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    actor_role: Mapped[str | None] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[str] = mapped_column(String(64))
    before_json: Mapped[Any | None] = mapped_column(JSON())
    after_json: Mapped[Any | None] = mapped_column(JSON())
    approval_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    approver_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    reason: Mapped[str | None] = mapped_column(String(512))
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    self_approved: Mapped[bool] = mapped_column(Boolean())
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


class AuditHead(Base):
    """每条哈希链一行。last_id 只是指针。不加外键。避免和审计写入互相卡住。"""

    __tablename__ = "audit_head"
    __table_args__ = (UniqueConstraint("chain", name="uq_audit_head_chain"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    chain: Mapped[str] = mapped_column(String(32))
    last_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    last_hash: Mapped[str | None] = mapped_column(String(64))


V01_TABLES: frozenset[str] = frozenset(Base.metadata.tables)
