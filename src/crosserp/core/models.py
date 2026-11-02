"""导入层校验模型。与 ORM 分开。不读写数据库。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from crosserp.core.enums import (
    FeeCategory,
    ImportStatus,
    IssueKind,
    IssueStatus,
    MatchStatus,
    Platform,
)


class ImportRecord(BaseModel):
    """导入层模型基类。金额字段拒绝 float。时间必须带时区。"""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _reject_float_and_naive_datetime(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        for key, value in data.items():
            if isinstance(value, float):
                raise ValueError(f"{key} 禁止 float")
            if isinstance(value, datetime) and (
                value.tzinfo is None or value.tzinfo.utcoffset(value) is None
            ):
                raise ValueError(f"{key} 时间必须带时区")
        return data


class ImportBatchRecord(ImportRecord):
    """一次导入批次。"""

    id: UUID
    connector_id: str = Field(max_length=64)
    connector_version: str = Field(max_length=32)
    file_name: str = Field(max_length=512)
    file_sha256: str = Field(min_length=64, max_length=64)
    imported_at: datetime
    row_count: int = Field(ge=0)
    status: ImportStatus
    error_count: int = Field(ge=0)


class RawRowRecord(ImportRecord):
    """原始行。id 由数据库自增。写入前可以没有。"""

    id: int | None = None
    batch_id: UUID
    row_no: int = Field(ge=1)
    payload_json: dict[str, Any]


class StoreRecord(ImportRecord):
    """店铺。"""

    id: UUID
    platform: Platform
    marketplace: str = Field(max_length=64)
    name: str = Field(max_length=255)
    currency: str = Field(min_length=3, max_length=3)


class SkuRecord(ImportRecord):
    """平台 SKU 映射。"""

    id: UUID
    store_id: UUID
    platform_sku: str = Field(max_length=128)
    internal_sku: str = Field(max_length=128)
    title: str | None = Field(default=None, max_length=512)
    active: bool


class SkuCostRecord(ImportRecord):
    """生效期内的单位成本。"""

    id: UUID
    internal_sku: str = Field(max_length=128)
    valid_from: datetime
    valid_to: datetime | None = None
    unit_cost: Decimal
    currency: str = Field(min_length=3, max_length=3)
    freight_per_unit: Decimal
    source_batch_id: UUID | None = None


class FxRateRecord(ImportRecord):
    """月汇率。period 为 YYYY-MM。"""

    id: UUID
    period: str = Field(min_length=7, max_length=7)
    from_ccy: str = Field(min_length=3, max_length=3)
    to_ccy: str = Field(min_length=3, max_length=3)
    rate: Decimal
    source: str = Field(max_length=128)


class OrderLineRecord(ImportRecord):
    """订单行。"""

    id: UUID
    store_id: UUID
    platform_order_id: str = Field(max_length=64)
    order_item_id: str | None = Field(default=None, max_length=64)
    platform_sku: str = Field(max_length=128)
    qty: int
    order_date: datetime
    item_price: Decimal | None = None
    currency: str = Field(min_length=3, max_length=3)
    source_batch_id: UUID
    raw_row_id: int | None = None


class SettlementRecord(ImportRecord):
    """一次结算或一次打款。"""

    id: UUID
    store_id: UUID
    platform: Platform
    external_id: str = Field(max_length=64)
    period_start: datetime
    period_end: datetime
    deposit_date: datetime | None = None
    total: Decimal
    currency: str = Field(min_length=3, max_length=3)
    source_batch_id: UUID


class SettlementLineRecord(ImportRecord):
    """结算明细。"""

    id: UUID
    settlement_id: UUID
    transaction_type: str = Field(max_length=64)
    order_id: str | None = Field(default=None, max_length=64)
    order_item_code: str | None = Field(default=None, max_length=64)
    sku: str | None = Field(default=None, max_length=128)
    qty: int | None = None
    amount_type: str | None = Field(default=None, max_length=64)
    amount_description: str | None = Field(default=None, max_length=512)
    amount: Decimal
    posted_at: datetime | None = None
    raw_row_id: int | None = None


class FeeRecord(ImportRecord):
    """分类后的费用。"""

    id: UUID
    settlement_line_id: UUID
    fee_category: FeeCategory
    amount: Decimal


class MatchRecord(ImportRecord):
    """匹配结果。组级匹配时 settlement_line_id 为空。"""

    id: UUID
    settlement_line_id: UUID | None = None
    order_line_id: UUID
    rule_id: str = Field(max_length=64)
    status: MatchStatus
    diff: Decimal
    matched_at: datetime


class IssueRecord(ImportRecord):
    """异常。"""

    id: UUID
    kind: IssueKind
    severity: str = Field(max_length=32)
    settlement_line_id: UUID | None = None
    order_line_id: UUID | None = None
    detail_json: dict[str, Any]
    status: IssueStatus
    resolution_note: str | None = Field(default=None, max_length=2000)
    created_at: datetime


class ProfitSnapshotRecord(ImportRecord):
    """利润快照。ads 为空表示未含广告。"""

    id: UUID
    period: str = Field(min_length=7, max_length=7)
    internal_sku: str = Field(max_length=128)
    store_id: UUID
    revenue: Decimal
    fees: Decimal
    refunds: Decimal
    cogs: Decimal
    freight: Decimal
    ads: Decimal | None = None
    profit: Decimal
    currency: str = Field(min_length=3, max_length=3)
    calc_version: str = Field(max_length=32)
    inputs_hash: str = Field(max_length=64)


class AuditLogRecord(ImportRecord):
    """业务审计记录。只追加。本模型不提供更新。"""

    id: UUID
    seq: int
    ts: datetime
    actor_type: str = Field(max_length=32)
    actor_user_id: UUID | None = None
    actor_role: str | None = Field(default=None, max_length=32)
    action: str = Field(max_length=64)
    target_type: str = Field(max_length=64)
    target_id: str = Field(max_length=64)
    before_json: dict[str, Any] | None = None
    after_json: dict[str, Any] | None = None
    approval_id: UUID | None = None
    approver_id: UUID | None = None
    reason: str | None = Field(default=None, max_length=512)
    request_id: str | None = Field(default=None, max_length=64)
    ip: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=512)
    self_approved: bool
    prev_hash: str = Field(min_length=64, max_length=64)
    hash: str = Field(min_length=64, max_length=64)


class AuditHeadRecord(ImportRecord):
    """哈希链头。空链的 last_id 与 last_hash 为空。"""

    id: UUID
    chain: str = Field(max_length=32)
    last_id: UUID | None = None
    last_hash: str | None = Field(default=None, max_length=64)


class RawRow(ImportRecord):
    """连接器读出的原始行。值保持字符串。金额不在这里解析。"""

    row_no: int = Field(ge=1)
    payload: dict[str, str]
    source_file: str = Field(min_length=1)


class Provenance(ImportRecord):
    """标准记录的出处。写入时由导入器填上批次 id。"""

    connector_id: str = Field(min_length=1, max_length=64)
    connector_version: str = Field(min_length=1, max_length=32)
    import_batch_id: UUID
    source_file: str = Field(min_length=1)
    row_no: int = Field(ge=1)
    # YAML source_name。没有映射时为空。T12 写入。
    source_name: str | None = Field(default=None, max_length=128)


class ColumnMapping(ImportRecord):
    """列映射。键是标准字段。值是源表头名。未列出的列仍留在原始行。"""

    target: str | None = Field(default=None, max_length=64)
    source_name: str | None = Field(default=None, max_length=128)
    sheet: int | str | None = None
    header_row: int = Field(default=1, ge=1)
    encoding: str = Field(default="utf-8-sig", max_length=32)
    amount_locale: Literal["us", "eu"] | None = None
    date_formats: list[str] = Field(default_factory=list)
    timezone: str | None = Field(default=None, max_length=64)
    columns: dict[str, str] = Field(default_factory=dict)
    defaults: dict[str, str] = Field(default_factory=dict)
    # 表头之后、数据之前再跳过的行数。表头之前的行由 header_row 跳过。
    skip_rows: int = Field(default=0, ge=0)


class SyncWindow(ImportRecord):
    """只读拉取的时间窗。v0.1 不实现 ApiConnector。"""

    start: datetime
    end: datetime


class Credentials(ImportRecord):
    """连接凭证。只在内存中传递。不要写入日志或审计。"""

    values: dict[str, str] = Field(default_factory=dict)


class _Canonical(ImportRecord):
    """标准记录公共字段。record_type 用来区分联合类型。"""

    provenance: Provenance | None = None


class SettlementHeader(_Canonical):
    """一次结算或一次打款的头。"""

    record_type: Literal["settlement_header"] = "settlement_header"
    platform: Platform
    external_id: str = Field(min_length=1, max_length=64)
    period_start: datetime
    period_end: datetime
    deposit_date: datetime | None = None
    total: Decimal
    currency: str = Field(min_length=3, max_length=3)
    marketplace: str = Field(min_length=1, max_length=64)
    store_name: str = Field(min_length=1, max_length=255)
    store_id: UUID | None = None


class SettlementLineRec(_Canonical):
    """一条结算明细。external_id 必须已经有结算头。"""

    record_type: Literal["settlement_line"] = "settlement_line"
    platform: Platform
    external_id: str = Field(min_length=1, max_length=64)
    transaction_type: str = Field(min_length=1, max_length=64)
    amount: Decimal
    order_id: str | None = Field(default=None, max_length=64)
    order_item_code: str | None = Field(default=None, max_length=64)
    sku: str | None = Field(default=None, max_length=128)
    qty: int | None = None
    amount_type: str | None = Field(default=None, max_length=64)
    amount_description: str | None = Field(default=None, max_length=512)
    posted_at: datetime | None = None
    fee_category: FeeCategory | None = None


class OrderLineRec(_Canonical):
    """一条订单。没有 store_id 时按店铺身份查找或创建。"""

    record_type: Literal["order_line"] = "order_line"
    platform: Platform
    marketplace: str = Field(min_length=1, max_length=64)
    store_name: str = Field(min_length=1, max_length=255)
    store_currency: str = Field(min_length=3, max_length=3)
    store_id: UUID | None = None
    platform_order_id: str = Field(min_length=1, max_length=64)
    order_item_id: str | None = Field(default=None, max_length=64)
    platform_sku: str = Field(min_length=1, max_length=128)
    qty: int
    order_date: datetime
    item_price: Decimal | None = None
    currency: str = Field(min_length=3, max_length=3)


class SkuCostRec(_Canonical):
    """一条单位成本。"""

    record_type: Literal["sku_cost"] = "sku_cost"
    internal_sku: str = Field(min_length=1, max_length=128)
    valid_from: datetime
    valid_to: datetime | None = None
    unit_cost: Decimal
    currency: str = Field(min_length=3, max_length=3)
    freight_per_unit: Decimal


class FxRateRec(_Canonical):
    """一条月汇率。"""

    record_type: Literal["fx_rate"] = "fx_rate"
    period: str = Field(min_length=7, max_length=7)
    from_ccy: str = Field(min_length=3, max_length=3)
    to_ccy: str = Field(min_length=3, max_length=3)
    rate: Decimal
    source: str = Field(min_length=1, max_length=128)


class SkuRec(_Canonical):
    """一条平台 SKU 映射。没有 store_id 时按店铺身份查找或创建。"""

    record_type: Literal["sku"] = "sku"
    platform: Platform
    marketplace: str = Field(min_length=1, max_length=64)
    store_name: str = Field(min_length=1, max_length=255)
    store_currency: str = Field(min_length=3, max_length=3)
    store_id: UUID | None = None
    platform_sku: str = Field(min_length=1, max_length=128)
    internal_sku: str = Field(min_length=1, max_length=128)
    title: str | None = Field(default=None, max_length=512)
    active: bool = True


class IssueRec(_Canonical):
    """连接器给出的异常。解析失败也可以由导入器直接写 issue。"""

    record_type: Literal["issue"] = "issue"
    issue_kind: IssueKind
    severity: str = Field(default="error", max_length=32)
    detail_json: dict[str, Any] = Field(default_factory=dict)
    status: IssueStatus = IssueStatus.OPEN


CanonicalRecord = Annotated[
    SettlementHeader
    | SettlementLineRec
    | OrderLineRec
    | SkuCostRec
    | FxRateRec
    | SkuRec
    | IssueRec,
    Field(discriminator="record_type"),
]
