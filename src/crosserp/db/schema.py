"""v0.1 业务表。字段按实施方案第 4 节。不建 v0.5 表。

金额列用 Money4。汇率用 FxRate。时间用 UtcDateTime。JSON 用 JSON。
分类字段用 String(32)。不用数据库原生 ENUM。要建索引的字符串长度不超过 255。
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects import mysql
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
_LONG_TEXT = Text().with_variant(mysql.MEDIUMTEXT(), "mysql")


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
    # P1 ingest 统一链路字段。旧导入入口继续使用同一张表。
    source: Mapped[str] = mapped_column(_KIND, default="file", server_default="file")
    kind: Mapped[str] = mapped_column(_KIND, default="unknown", server_default="unknown")
    mapping_rule_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    counts_json: Mapped[Any | None] = mapped_column(JSON(), default=dict, nullable=True)
    landed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    valid_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    quarantined_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    projected_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    on_behalf_of: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)


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
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)


# 领域名称与历史表名的兼容别名：P1 不建立第二套 raw/import 表。  # noqa: RUF003
IngestBatch = ImportBatch
RawRecord = RawRow


class CleansingIssue(Base):
    """清洗隔离区中的一条问题记录。"""

    __tablename__ = "cleansing_issue"
    __table_args__ = (
        Index("ix_cleansing_issue_batch_id", "batch_id"),
        Index("ix_cleansing_issue_raw_record_id", "raw_record_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("import_batch.id"))
    raw_record_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("raw_row.id"))
    row_no: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(_KIND)
    field: Mapped[str | None] = mapped_column(String(128), nullable=True)
    message: Mapped[str] = mapped_column(String(1000))
    suggestion_json: Mapped[Any | None] = mapped_column(JSON(), default=dict, nullable=True)
    status: Mapped[str] = mapped_column(_KIND, default="open", server_default="open")
    handler: Mapped[str | None] = mapped_column(_KIND, nullable=True)
    agent_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    assignee_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("app_user.id"), nullable=True
    )
    money_impact: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    resolution_json: Mapped[Any | None] = mapped_column(JSON(), nullable=True)
    escalation_json: Mapped[Any | None] = mapped_column(JSON(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    updated_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)


class CleansingIssueTransfer(Base):
    """清洗问题转交记录; 通知模块接入前作为站内待办的持久化记录。"""

    __tablename__ = "cleansing_issue_transfer"
    __table_args__ = (
        Index("ix_cleansing_issue_transfer_issue_id", "issue_id"),
        Index("ix_cleansing_issue_transfer_assignee", "assignee_user_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("import_batch.id"))
    issue_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("cleansing_issue.id"))
    assignee_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("app_user.id"))
    actor_type: Mapped[str] = mapped_column(String(16))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    on_behalf_of: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    attempts_json: Mapped[Any] = mapped_column(JSON(), default=list)
    evidence_json: Mapped[Any] = mapped_column(JSON(), default=list)
    suggestion_json: Mapped[Any | None] = mapped_column(JSON(), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class MappingRule(Base):
    """按规则键和版本保留的映射规则。"""

    __tablename__ = "mapping_rule"
    __table_args__ = (
        UniqueConstraint("rule_key", "rule_version", name="uq_mapping_rule_key_version"),
        Index("ix_mapping_rule_key", "rule_key"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    rule_key: Mapped[str] = mapped_column(String(128))
    rule_version: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(_KIND)
    body_json: Mapped[Any] = mapped_column(JSON())
    status: Mapped[str] = mapped_column(_KIND, default="active", server_default="active")
    verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class Store(Base):
    """店铺。"""

    __tablename__ = "store"

    id: Mapped[uuid.UUID] = _uuid_pk()
    platform: Mapped[str] = mapped_column(_KIND)
    marketplace: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    currency: Mapped[str] = mapped_column(String(3))
    legal_entity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)


class Category(Base):
    """商品类目树。版本由实体动作版本链同步维护。"""

    __tablename__ = "category"
    __table_args__ = (
        Index("ix_category_parent_id", "parent_id"),
        UniqueConstraint("parent_id", "name", name="uq_category_parent_name"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("category.id"), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="1")
    version: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())


class Brand(Base):
    """商品品牌主数据。"""

    __tablename__ = "brand"
    __table_args__ = (Index("ix_brand_name", "name"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="1")
    version: Mapped[int] = mapped_column(Integer(), default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    provenance: Mapped[Any] = mapped_column(JSON(), nullable=False, default=dict)


class Sku(Base):
    """平台 SKU 与内部 SKU 的映射。"""

    __tablename__ = "sku"
    __table_args__ = (
        UniqueConstraint("store_id", "platform_sku", name="uq_sku_store_platform_sku"),
        Index("ix_sku_brand_id", "brand_id"),
        Index("ix_sku_category_id", "category_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    store_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("store.id"))
    platform_sku: Mapped[str] = mapped_column(String(128))
    internal_sku: Mapped[str] = mapped_column(String(128))
    title: Mapped[str | None] = mapped_column(String(512))
    title_en: Mapped[str | None] = mapped_column(String(512))
    brand_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("brand.id"))
    category_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("category.id"))
    uom: Mapped[str | None] = mapped_column(String(32))
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    hs_code: Mapped[str | None] = mapped_column(String(32))
    aliases_json: Mapped[list[str]] = mapped_column(JSON(), nullable=False, default=list)
    active: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="1")
    created_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    updated_at: Mapped[datetime | None] = mapped_column(UtcDateTime())


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


class FeeReference(Base):
    """按 SKU、生效期存放的配送费参考值。"""

    __tablename__ = "fee_reference"
    __table_args__ = (
        Index("ix_fee_reference_internal_sku", "internal_sku"),
        Index("ix_fee_reference_source_batch_id", "source_batch_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    store_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("store.id"))
    internal_sku: Mapped[str] = mapped_column(String(64))
    fee_category: Mapped[str] = mapped_column(_KIND)
    currency: Mapped[str] = mapped_column(String(3))
    expected_per_unit: Mapped[Decimal] = mapped_column(Money4())
    valid_from: Mapped[datetime] = mapped_column(UtcDateTime())
    valid_to: Mapped[datetime | None] = mapped_column(UtcDateTime())
    source_batch_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("import_batch.id"))


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
    __table_args__ = (
        Index("ix_profit_snapshot_store_id", "store_id"),
        Index("ix_profit_snapshot_recon_run_id", "recon_run_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    period: Mapped[str] = mapped_column(String(7))
    internal_sku: Mapped[str] = mapped_column(String(128))
    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("store.id"))
    revenue: Mapped[Decimal] = mapped_column(Money4())
    fees: Mapped[Decimal] = mapped_column(Money4())
    refunds: Mapped[Decimal] = mapped_column(Money4())
    cogs: Mapped[Decimal | None] = mapped_column(Money4())
    freight: Mapped[Decimal | None] = mapped_column(Money4())
    ads: Mapped[Decimal | None] = mapped_column(Money4())
    profit: Mapped[Decimal | None] = mapped_column(Money4())
    currency: Mapped[str] = mapped_column(String(3))
    calc_version: Mapped[str] = mapped_column(String(32))
    inputs_hash: Mapped[str] = mapped_column(String(64))
    qty_sold: Mapped[int] = mapped_column(Integer, default=0)
    qty_refunded: Mapped[int] = mapped_column(Integer, default=0)
    qty_net: Mapped[int] = mapped_column(Integer, default=0)
    promotion: Mapped[Decimal] = mapped_column(Money4(), default=Decimal(0))
    fx_rate: Mapped[Decimal | None] = mapped_column(FxRateColumn())
    profit_cny: Mapped[Decimal | None] = mapped_column(Money4())
    ads_included: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(_KIND, default="ok")
    recon_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("recon_run.id"))


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
    actor_name: Mapped[str | None] = mapped_column(String(64))
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
    hash_version: Mapped[int] = mapped_column(Integer, default=2, server_default="2")
    agent_id: Mapped[str | None] = mapped_column(String(128))
    on_behalf_of: Mapped[str | None] = mapped_column(String(128))
    delegation_id: Mapped[str | None] = mapped_column(String(128))
    run_id: Mapped[str | None] = mapped_column(String(128))
    tool_call_id: Mapped[str | None] = mapped_column(String(128))
    is_subagent: Mapped[Any] = mapped_column(JSON(), default=False, nullable=True)
    subagent_name: Mapped[str | None] = mapped_column(String(128))
    channel: Mapped[str | None] = mapped_column(String(32))
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(128))
    diff_json: Mapped[Any | None] = mapped_column(JSON())
    evidence_json: Mapped[Any | None] = mapped_column(JSON())
    model: Mapped[str | None] = mapped_column(String(128))
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    llm_call: Mapped[str | None] = mapped_column(String(128))
    confidence: Mapped[Any | None] = mapped_column(JSON())
    autonomy_level: Mapped[str | None] = mapped_column(String(16))


class AuditHead(Base):
    """每条哈希链一行。last_id 只是指针。不加外键。避免和审计写入互相卡住。"""

    __tablename__ = "audit_head"
    __table_args__ = (UniqueConstraint("chain", name="uq_audit_head_chain"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    chain: Mapped[str] = mapped_column(String(32))
    last_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    last_hash: Mapped[str | None] = mapped_column(String(64))


class Approval(Base):
    """一张审批单。token 只在批准时返回一次，数据库只保存其哈希。"""  # noqa: RUF002

    __tablename__ = "approval"
    __table_args__ = (Index("ix_approval_target_type_target_id", "target_type", "target_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    target_type: Mapped[str] = mapped_column(String(32))
    target_id: Mapped[str] = mapped_column(String(128))
    state: Mapped[str] = mapped_column(String(32))
    payload_hash: Mapped[str | None] = mapped_column(String(64))
    requested_by: Mapped[str] = mapped_column(String(64))
    requested_at: Mapped[datetime] = mapped_column(UtcDateTime())
    approver: Mapped[str | None] = mapped_column(String(64))
    decided_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    comment: Mapped[str | None] = mapped_column(String(1000))
    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    used_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    approval_type: Mapped[str | None] = mapped_column(String(64))
    risk_tier: Mapped[str | None] = mapped_column(String(16))
    actor_type: Mapped[str] = mapped_column(String(16), default="human", server_default="human")
    on_behalf_of: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    resolution: Mapped[Any | None] = mapped_column(JSON())
    content_hash: Mapped[str | None] = mapped_column(String(64))
    initiator_confirmed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    initiator_confirmed_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    initiator_confirmation_hash: Mapped[str | None] = mapped_column(String(64))
    approver_ids: Mapped[Any | None] = mapped_column(JSON())
    current_step: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class ApprovalType(Base):
    __tablename__ = "approval_type"
    id: Mapped[uuid.UUID] = _uuid_pk()
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    risk_tier: Mapped[str] = mapped_column(String(16))
    enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="1")
    template_json: Mapped[Any | None] = mapped_column(JSON())
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class WorkflowRule(Base):
    __tablename__ = "workflow_rule"
    __table_args__ = (
        UniqueConstraint("approval_type", "version", name="uq_workflow_rule_type_version"),
    )
    id: Mapped[uuid.UUID] = _uuid_pk()
    approval_type: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer)
    steps_json: Mapped[Any] = mapped_column(JSON())
    enabled: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="1")
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())


class AuditAlert(Base):
    __tablename__ = "audit_alert"
    id: Mapped[uuid.UUID] = _uuid_pk()
    kind: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="open", server_default="open")
    detail_json: Mapped[Any | None] = mapped_column(JSON())
    audit_log_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    resolved_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())


class RetentionPolicy(Base):
    __tablename__ = "retention_policy"
    id: Mapped[uuid.UUID] = _uuid_pk()
    chain: Mapped[str] = mapped_column(String(32), unique=True)
    retain_days: Mapped[int] = mapped_column(Integer, default=3650, server_default="3650")
    archive_before: Mapped[datetime | None] = mapped_column(UtcDateTime())
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())


class ArchiveRun(Base):
    __tablename__ = "audit_archive_run"
    id: Mapped[uuid.UUID] = _uuid_pk()
    chain: Mapped[str] = mapped_column(String(32))
    upto_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    upto_hash: Mapped[str] = mapped_column(String(64))
    row_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class Voucher(Base):
    """凭证草稿及其输入/科目配置哈希。"""

    __tablename__ = "voucher"
    __table_args__ = (
        Index("ix_voucher_store_period", "store_id", "period"),
        CheckConstraint(
            "total_debit >= 0 AND total_credit >= 0", name="voucher_totals_nonnegative"
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("store.id"))
    period: Mapped[str] = mapped_column(String(7))
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(128))
    state: Mapped[str] = mapped_column(String(16))
    currency: Mapped[str] = mapped_column(String(3))
    total_debit: Mapped[Decimal] = mapped_column(Money4())
    total_credit: Mapped[Decimal] = mapped_column(Money4())
    inputs_hash: Mapped[str] = mapped_column(String(64))
    accounts_hash: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class VoucherLine(Base):
    """凭证分录, 每行只能填借方或贷方。"""

    __tablename__ = "voucher_line"
    __table_args__ = (
        Index("ix_voucher_line_voucher_id", "voucher_id"),
        CheckConstraint(
            "debit >= 0 AND credit >= 0 AND NOT (debit > 0 AND credit > 0)",
            name="voucher_line_one_side",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    voucher_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("voucher.id"))
    line_no: Mapped[int] = mapped_column(Integer)
    account_key: Mapped[str] = mapped_column(String(64))
    account_code: Mapped[str] = mapped_column(String(32))
    account_name: Mapped[str] = mapped_column(String(128))
    debit: Mapped[Decimal] = mapped_column(Money4())
    credit: Mapped[Decimal] = mapped_column(Money4())
    summary: Mapped[str] = mapped_column(String(200))
    source_ref: Mapped[str] = mapped_column(String(128))


class PromptVersion(Base):
    __tablename__ = "prompt_version"
    __table_args__ = (UniqueConstraint("name", "sha256", name="uq_prompt_version_name_sha256"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(32))
    sha256: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(_LONG_TEXT)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class LlmCall(Base):
    __tablename__ = "llm_call"

    id: Mapped[uuid.UUID] = _uuid_pk()
    ts: Mapped[datetime] = mapped_column(UtcDateTime())
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    username: Mapped[str | None] = mapped_column(String(64))
    channel: Mapped[str] = mapped_column(String(16))
    model: Mapped[str] = mapped_column(String(128))
    prompt_version_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("prompt_version.id"))
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[int] = mapped_column(Integer)
    cost_estimate: Mapped[Decimal | None] = mapped_column(Money4())
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(16))
    refusal_reason: Mapped[str | None] = mapped_column(String(512))
    question_text: Mapped[str | None] = mapped_column(_LONG_TEXT)
    answer_text: Mapped[str | None] = mapped_column(_LONG_TEXT)
    trace_id: Mapped[str] = mapped_column(String(32))
    request_id: Mapped[str | None] = mapped_column(String(64))


class LlmToolCall(Base):
    __tablename__ = "llm_tool_call"
    __table_args__ = (Index("ix_llm_tool_call_llm_call_id", "llm_call_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    llm_call_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("llm_call.id"))
    seq: Mapped[int] = mapped_column(Integer)
    tool_name: Mapped[str] = mapped_column(String(64))
    args_json: Mapped[Any] = mapped_column(JSON())
    result_rows: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))


class LlmBudget(Base):
    __tablename__ = "llm_budget"
    id: Mapped[uuid.UUID] = _uuid_pk()
    scope: Mapped[str] = mapped_column(String(16))
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    period: Mapped[str] = mapped_column(String(7))
    limit_amount: Mapped[Decimal | None] = mapped_column(Money4())
    limit_tokens: Mapped[int | None] = mapped_column(BigInteger())
    currency: Mapped[str] = mapped_column(String(3))
    warn_percent: Mapped[int] = mapped_column(Integer, default=80, server_default="80")
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class LlmAlert(Base):
    __tablename__ = "llm_alert"
    id: Mapped[uuid.UUID] = _uuid_pk()
    ts: Mapped[datetime] = mapped_column(UtcDateTime())
    budget_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("llm_budget.id"))
    kind: Mapped[str] = mapped_column(String(16))
    used_amount: Mapped[Decimal] = mapped_column(Money4())
    used_tokens: Mapped[int] = mapped_column(BigInteger())
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    acknowledged_at: Mapped[datetime | None] = mapped_column(UtcDateTime())


class EvalRun(Base):
    __tablename__ = "eval_run"
    id: Mapped[uuid.UUID] = _uuid_pk()
    ts: Mapped[datetime] = mapped_column(UtcDateTime())
    model: Mapped[str] = mapped_column(String(128))
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    git_sha: Mapped[str] = mapped_column(String(40))
    total: Mapped[int] = mapped_column(Integer)
    passed: Mapped[int] = mapped_column(Integer)
    details_json: Mapped[Any] = mapped_column(JSON())
    triggered_by: Mapped[str] = mapped_column(String(64))


class ExportArtifact(Base):
    """一次审批后的外部文件产物。"""

    __tablename__ = "export_artifact"
    __table_args__ = (Index("ix_export_artifact_approval_id", "approval_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    approval_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("approval.id"))
    target_id: Mapped[str] = mapped_column(String(32))
    file_path: Mapped[str | None] = mapped_column(String(1000))
    ext_ref: Mapped[str | None] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class AuditCheckpoint(Base):
    """审计保留锚点。创建检查点不删除任何日志。"""

    __tablename__ = "audit_checkpoint"
    __table_args__ = (Index("ix_audit_checkpoint_chain_created_at", "chain", "created_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    chain: Mapped[str] = mapped_column(String(32))
    upto_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    upto_hash: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class AuditExport(Base):
    """一次审计包导出的索引记录。"""

    __tablename__ = "audit_export"

    id: Mapped[uuid.UUID] = _uuid_pk()
    requested_by: Mapped[str] = mapped_column(String(64))
    from_ts: Mapped[datetime] = mapped_column(UtcDateTime())
    to_ts: Mapped[datetime] = mapped_column(UtcDateTime())
    format: Mapped[str] = mapped_column(String(16))
    row_count: Mapped[int] = mapped_column(Integer)
    first_hash: Mapped[str | None] = mapped_column(String(64))
    last_hash: Mapped[str | None] = mapped_column(String(64))
    file_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class AppUser(Base):
    """登录用户。用户只停用, 不物理删除。"""

    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = _uuid_pk()
    username: Mapped[str] = mapped_column(String(64), unique=True)
    display_name: Mapped[str] = mapped_column(String(128))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    failed_logins: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(UtcDateTime())
    password_changed_at: Mapped[datetime] = mapped_column(UtcDateTime())
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    permission_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class UserRole(Base):
    """用户角色, 多角色可叠加。"""

    __tablename__ = "user_role"
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("app_user.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(64), primary_key=True)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    granted_at: Mapped[datetime] = mapped_column(UtcDateTime())


class UserSession(Base):
    """服务器端登录会话; id 存 token 的 sha256, 不存明文 cookie。"""

    __tablename__ = "user_session"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime())
    last_seen_at: Mapped[datetime] = mapped_column(UtcDateTime())
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    csrf_token_hash: Mapped[str] = mapped_column(String(64))
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime())


class ApiToken(Base):
    """API token 只保存哈希, 实际 token 由 T47 使用。"""

    __tablename__ = "api_token"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("app_user.id"))
    name: Mapped[str] = mapped_column(String(64))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    scopes: Mapped[Any] = mapped_column(JSON())
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    last_used_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime())


class AppSetting(Base):
    """可审计的系统设置。"""

    __tablename__ = "app_setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value_json: Mapped[Any] = mapped_column(JSON())
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())


class SecurityEvent(Base):
    """登录和权限事件独立哈希链。"""

    __tablename__ = "security_event"
    __table_args__ = (
        UniqueConstraint("seq", name="uq_security_event_seq"),
        Index("ix_security_event_ts", "ts"),
        Index("ix_security_event_user_ts", "user_id", "ts"),
        Index("ix_security_event_event_ts", "event", "ts"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    seq: Mapped[int] = mapped_column(Integer)
    ts: Mapped[datetime] = mapped_column(UtcDateTime())
    event: Mapped[str] = mapped_column(String(32))
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    username: Mapped[str | None] = mapped_column(String(64))
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    request_id: Mapped[str | None] = mapped_column(String(64))
    detail_json: Mapped[Any | None] = mapped_column(JSON())
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


class IdempotencyKey(Base):
    """JSON API 幂等键及首次响应; 过期记录可由维护任务清理。"""

    __tablename__ = "idempotency_key"
    __table_args__ = (Index("ix_idempotency_key_expires_at", "expires_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    status_code: Mapped[int] = mapped_column(Integer)
    response_body: Mapped[str] = mapped_column(Text())
    response_headers: Mapped[Any] = mapped_column(JSON(), default=dict)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime())


class PasswordResetToken(Base):
    """一次性密码重置令牌只保存摘要。"""

    __tablename__ = "password_reset_token"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("app_user.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime())
    used_at: Mapped[datetime | None] = mapped_column(UtcDateTime())


class FileObject(Base):
    """上传文件元数据；内容保存在配置目录，sha256 唯一去重。"""  # noqa: RUF002

    __tablename__ = "file_object"
    __table_args__ = (UniqueConstraint("sha256", name="uq_file_object_sha256"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    sha256: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str | None] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(BigInteger())
    storage_path: Mapped[str] = mapped_column(String(1000))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class Job(Base):
    """CrossERP 自调度任务记录。"""

    __tablename__ = "job"

    id: Mapped[uuid.UUID] = _uuid_pk()
    kind: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    progress: Mapped[Decimal] = mapped_column(Numeric(6, 5), default=Decimal("0"))
    payload_json: Mapped[Any] = mapped_column(JSON(), default=dict)
    error: Mapped[str | None] = mapped_column(String(2000))
    result_ref: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    started_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime())


class DocumentLink(Base):
    """单据关联通用边，后续业务域填充。"""  # noqa: RUF002

    __tablename__ = "document_link"
    __table_args__ = (
        Index("ix_document_link_from", "from_type", "from_id"),
        Index("ix_document_link_to", "to_type", "to_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    from_type: Mapped[str] = mapped_column(String(64))
    from_id: Mapped[str] = mapped_column(String(128))
    to_type: Mapped[str] = mapped_column(String(64))
    to_id: Mapped[str] = mapped_column(String(128))
    relation: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class Delegation(Base):
    """会话委托通行证和登出作废钩子所需的最小记录。"""

    __tablename__ = "delegation"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("app_user.id"))
    session_id: Mapped[str] = mapped_column(String(64))
    run_id: Mapped[str | None] = mapped_column(String(128))
    scopes: Mapped[Any] = mapped_column(JSON(), default=list)
    status: Mapped[str] = mapped_column(String(16), default="active")
    revoke_reason: Mapped[str | None] = mapped_column(String(32))
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime())
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class EntityVersion(Base):
    """实体动作产生的不可变版本快照。"""

    __tablename__ = "entity_version"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "version", name="uq_entity_version_number"),
        Index("ix_entity_version_entity", "entity_type", "entity_id", "version"),
        Index("ix_entity_version_batch", "source_batch_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer)
    changed_at: Mapped[datetime] = mapped_column(UtcDateTime())
    actor_type: Mapped[str] = mapped_column(String(16))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    on_behalf_of: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    delegation_id: Mapped[str | None] = mapped_column(String(64))
    run_id: Mapped[str | None] = mapped_column(String(64))
    is_subagent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    channel: Mapped[str] = mapped_column(String(32), default="web", server_default="web")
    action_id: Mapped[str | None] = mapped_column(String(128))
    source_batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    source_raw_row_id: Mapped[int | None] = mapped_column(BigInteger())
    source_file: Mapped[str | None] = mapped_column(String(512))
    before_json: Mapped[Any | None] = mapped_column(JSON())
    after_json: Mapped[Any | None] = mapped_column(JSON())
    diff_json: Mapped[Any | None] = mapped_column(JSON())
    audit_log_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())


class ActionExecution(Base):
    """动作幂等记录; 与实体版本和审计在同一事务中写入。"""

    __tablename__ = "action_execution"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_action_execution_idempotency"),
        Index("ix_action_execution_entity", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    idempotency_key: Mapped[str | None] = mapped_column(String(255))
    request_hash: Mapped[str | None] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    action_id: Mapped[str] = mapped_column(String(128))
    actor_type: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32))
    result_json: Mapped[Any | None] = mapped_column(JSON())
    approval_id: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    version: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class EntityEvent(Base):
    """动作产生的领域事件, 供站内摘要和后续订阅使用。"""

    __tablename__ = "entity_event"
    __table_args__ = (Index("ix_entity_event_entity", "entity_type", "entity_id", "created_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    event_type: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    action_id: Mapped[str | None] = mapped_column(String(128))
    payload_json: Mapped[Any] = mapped_column(JSON())
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class IamRole(Base):
    """权限模板/自定义角色。"""

    __tablename__ = "iam_role"

    id: Mapped[uuid.UUID] = _uuid_pk()
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    parent_ids: Mapped[Any] = mapped_column(JSON(), default=list)
    permissions: Mapped[Any] = mapped_column(JSON(), default=dict)
    data_scopes: Mapped[Any] = mapped_column(JSON(), default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    is_template: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())


class IamRolePermission(Base):
    """角色权限点明细, 与 JSON 快照保持一致并便于查询审计。"""

    __tablename__ = "iam_role_permission"
    __table_args__ = (UniqueConstraint("role_id", "permission"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    role_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("iam_role.id"))
    permission: Mapped[str] = mapped_column(String(128))
    effect: Mapped[str] = mapped_column(String(8))


class IamRoleInheritance(Base):
    """角色继承关系。"""

    __tablename__ = "iam_role_inheritance"
    __table_args__ = (UniqueConstraint("role_id", "parent_role_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    role_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("iam_role.id"))
    parent_role_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("iam_role.id"))


class IamPermissionOverride(Base):
    __tablename__ = "iam_permission_override"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("app_user.id"))
    permission: Mapped[str] = mapped_column(String(128))
    effect: Mapped[str] = mapped_column(String(8))
    reason: Mapped[str] = mapped_column(String(512))
    data_scopes: Mapped[Any] = mapped_column(JSON(), default=list)
    starts_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class IamTemporaryGrant(Base):
    __tablename__ = "iam_temporary_grant"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("app_user.id"))
    permission: Mapped[str] = mapped_column(String(128))
    effect: Mapped[str] = mapped_column(String(8))
    reason: Mapped[str] = mapped_column(String(512))
    starts_at: Mapped[datetime] = mapped_column(UtcDateTime())
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime())
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class IamFieldPolicy(Base):
    __tablename__ = "iam_field_policy"

    id: Mapped[uuid.UUID] = _uuid_pk()
    field_key: Mapped[str] = mapped_column(String(128), unique=True)
    permission: Mapped[str] = mapped_column(String(128))
    masked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())


class IamDataScopeRule(Base):
    __tablename__ = "iam_data_scope_rule"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(128))
    entity: Mapped[str] = mapped_column(String(128))
    scope_type: Mapped[str] = mapped_column(String(32))
    values: Mapped[Any] = mapped_column(JSON(), default=list)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())


class IamAccessReview(Base):
    __tablename__ = "iam_access_review"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("app_user.id"))
    state: Mapped[str] = mapped_column(String(16), default="open")
    snapshot: Mapped[Any] = mapped_column(JSON(), default=dict)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    reviewed_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())


class IamSodRule(Base):
    __tablename__ = "iam_sod_rule"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(128))
    permissions: Mapped[Any] = mapped_column(JSON(), default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())


class IamModuleSwitch(Base):
    __tablename__ = "iam_module_switch"

    module: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    config: Mapped[Any] = mapped_column(JSON(), default=dict)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())


class IamDictionary(Base):
    __tablename__ = "iam_dictionary"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    values: Mapped[Any] = mapped_column(JSON(), default=list)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())


class IamSystemSetting(Base):
    """权限治理相关系统参数。"""

    __tablename__ = "iam_system_setting"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON(), default=dict)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())


V01_TABLES: frozenset[str] = frozenset(Base.metadata.tables)
