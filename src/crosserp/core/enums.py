"""v0.1 枚举。数据库存 String(32)。不用原生 ENUM。"""

from __future__ import annotations

from enum import StrEnum


class Platform(StrEnum):
    """店铺或结算来源。"""

    AMAZON = "amazon"
    SHOPIFY = "shopify"
    LINGXING = "lingxing"
    SELLFOX = "sellfox"
    OTHER = "other"


class ImportStatus(StrEnum):
    """导入批次状态。取值推断自 T09。running / done / failed。"""

    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class FeeCategory(StrEnum):
    """费用分类。principal / shipping_charge 来自实施方案 6.4。"""

    COMMISSION = "commission"
    FBA = "fba"
    SHIPPING = "shipping"
    PROMOTION = "promotion"
    REFUND = "refund"
    ADS = "ads"
    OTHER = "other"
    PRINCIPAL = "principal"
    SHIPPING_CHARGE = "shipping_charge"


class IssueKind(StrEnum):
    """对账原因码。含实施方案 6.1 的 13 个码, 以及 maken 于 2026-11-02 确认的 5 个码。"""

    NOT_IN_ERP = "NOT_IN_ERP"
    NOT_IN_SETTLEMENT = "NOT_IN_SETTLEMENT"
    QTY_MISMATCH = "QTY_MISMATCH"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    SKU_UNMAPPED = "SKU_UNMAPPED"
    COST_MISSING = "COST_MISSING"
    FX_MISSING = "FX_MISSING"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    DUPLICATE_ROW = "DUPLICATE_ROW"
    REFUND_WITHOUT_ORDER = "REFUND_WITHOUT_ORDER"
    UNKNOWN_FEE_TYPE = "UNKNOWN_FEE_TYPE"
    SETTLEMENT_UNBALANCED = "SETTLEMENT_UNBALANCED"
    PARSE_ERROR = "PARSE_ERROR"
    FEE_OVERCHARGE = "FEE_OVERCHARGE"
    SETTLEMENT_DELAYED = "SETTLEMENT_DELAYED"
    CHARGEBACK = "CHARGEBACK"
    PARTIAL_REFUND = "PARTIAL_REFUND"
    DUPLICATE_SETTLEMENT = "DUPLICATE_SETTLEMENT"


class IssueStatus(StrEnum):
    """异常处理状态。"""

    OPEN = "open"
    EXPLAINED = "explained"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class MatchStatus(StrEnum):
    """匹配状态。未匹配不进本枚举。必须另有 issue。"""

    MATCHED = "matched"
    PARTIAL = "partial"
