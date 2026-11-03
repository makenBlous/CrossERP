"""合成样本用的平台取值。

不是平台字段全集。每个取值旁都注明「待真实数据验证」。
拿到真实文件后只改这个文件。不要在生成器里散落字面量。
"""

from __future__ import annotations

# 官方 24 列。来源是实施方案 5.1 与 SP-API Settlement Reports。
# 列名已核实。列里的取值不是全集。
AMAZON_V2_COLUMNS: tuple[str, ...] = (
    "settlement-id",
    "settlement-start-date",
    "settlement-end-date",
    "deposit-date",
    "total-amount",
    "currency",
    "transaction-type",
    "order-id",
    "merchant-order-id",
    "adjustment-id",
    "shipment-id",
    "marketplace-name",
    "amount-type",
    "amount-description",
    "amount",
    "fulfillment-id",
    "posted-date",
    "posted-date-time",
    "order-item-code",
    "merchant-order-item-id",
    "merchant-adjustment-item-id",
    "sku",
    "quantity-purchased",
    "promotion-id",
)

# transaction-type。待真实数据验证。不是全集。
TX_ORDER = "Order"  # 待真实数据验证
TX_REFUND = "Refund"  # 待真实数据验证
TX_CHARGEBACK = "Chargeback"  # 待真实数据验证
TX_OTHER = "other-transaction"  # 待真实数据验证。非订单类。不进匹配率分母。

# 订单类。推断 Order / Refund / Chargeback 按订单号合并。待真实数据验证。
ORDER_TRANSACTION_TYPES: frozenset[str] = frozenset({TX_ORDER, TX_REFUND, TX_CHARGEBACK})

# amount-type。待真实数据验证。不是全集。
AMOUNT_TYPE_PRICE = "ItemPrice"  # 待真实数据验证
AMOUNT_TYPE_FEE = "ItemFees"  # 待真实数据验证

# amount-description。待真实数据验证。不是全集。
DESC_PRINCIPAL = "Principal"  # 待真实数据验证
DESC_COMMISSION = "Commission"  # 待真实数据验证
DESC_FBA = "FBAPerUnitFulfillmentFee"  # 待真实数据验证
DESC_UNKNOWN = "SyntheticUnknownFee"  # 待真实数据验证。故意不在已知费用组合里。

# (amount-type, amount-description, fee_category)。合成已知组合。不是真实费率表。
# 每条都待真实数据验证。T10 的 fee_map 初版应只收录这里的组合。
KNOWN_FEE_PAIRS: tuple[tuple[str, str, str], ...] = (
    (AMOUNT_TYPE_PRICE, DESC_PRINCIPAL, "principal"),  # 待真实数据验证
    (AMOUNT_TYPE_FEE, DESC_COMMISSION, "commission"),  # 待真实数据验证
    (AMOUNT_TYPE_FEE, DESC_FBA, "fba"),  # 待真实数据验证
)

# marketplace-name。待真实数据验证。
# locale_for() 对 marketplace 做 casefold。"Amazon.de" 能对上 money.EU_MARKETPLACES 里的 amazon.de。
MARKETPLACE_US = "Amazon.com"  # 待真实数据验证
MARKETPLACE_DE = "Amazon.de"  # 待真实数据验证

# 日期格式。待真实数据验证。生成器只输出这一种。解析器以后要多格式兼容。
AMAZON_DATE = "%Y-%m-%d"  # 待真实数据验证
AMAZON_DATETIME_SUFFIX = "12:00:00 UTC"  # 待真实数据验证。拼在日期后。中间一个空格。

# fulfillment-id。待真实数据验证。
FULFILLMENT_AFN = "AFN"  # 待真实数据验证

# 汇总行 transaction-type 为空且 total-amount 非空。推断。待真实数据验证。
# 明细行重复 settlement-id / 日期 / currency。total-amount 留空。推断。待真实数据验证。

# Shopify 官方 11 个基础列。来源是实施方案 5.2。列名已核实。取值不是全集。
SHOPIFY_COLUMNS: tuple[str, ...] = (
    "Transaction Date",
    "Type",
    "Order",
    "Card Brand",
    "Card Source",
    "Payout Status",
    "Payout Date",
    "Available On",
    "Amount",
    "Fee",
    "Net",
)

# Type。待真实数据验证。不是全集。
SHOPIFY_TYPE_CHARGE = "charge"  # 待真实数据验证
SHOPIFY_TYPE_REFUND = "refund"  # 待真实数据验证
SHOPIFY_TYPE_DISPUTE = "dispute"  # 待真实数据验证

# 订单类 Type。推断。待真实数据验证。
SHOPIFY_ORDER_TYPES: frozenset[str] = frozenset(
    {SHOPIFY_TYPE_CHARGE, SHOPIFY_TYPE_REFUND, SHOPIFY_TYPE_DISPUTE}
)

# Payout Status。待真实数据验证。不是全集。
SHOPIFY_STATUS_PAID = "paid"  # 待真实数据验证。当作已打款。
SHOPIFY_STATUS_PENDING = "pending"  # 待真实数据验证。当作未打款。

# Transaction Date 示例形态。待真实数据验证。
SHOPIFY_DATETIME_EXAMPLE = "2026-10-03 10:15:00 -0400"  # 待真实数据验证

# Card Brand / Card Source。合成占位。待真实数据验证。
SHOPIFY_CARD_BRAND = "Visa"  # 待真实数据验证
SHOPIFY_CARD_SOURCE = "online"  # 待真实数据验证

# 导致订单类结算行组未匹配的原因码。实施方案 6.1。
# Shopify「Net ≠ Amount - Fee」也用 AMOUNT_MISMATCH。并计入未匹配组。
UNMATCHED_ISSUE_KINDS: frozenset[str] = frozenset(
    {
        "NOT_IN_ERP",
        "REFUND_WITHOUT_ORDER",
        "QTY_MISMATCH",
        "AMOUNT_MISMATCH",
        "SKU_UNMAPPED",
    }
)

# 场景表每一类。anomalies.json 的 scenario 必须覆盖这些键。
REQUIRED_SCENARIOS: tuple[str, ...] = (
    "normal",
    "fee_overcharge",
    "in_transit",
    "refund",
    "partial_refund",
    "chargeback",
    "refund_without_order",
    "not_in_erp",
    "qty_mismatch",
    "amount_mismatch",
    "sku_unmapped",
    "cost_missing",
    "fx_missing",
    "unknown_fee_type",
    "settlement_unbalanced",
    "shopify_net_mismatch",
    "duplicate_row",
)

SEED = 20261109
GRACE_DAYS = 14

FILE_ORDERS = "orders.csv"
FILE_COSTS = "costs.csv"
FILE_COSTS_XLSX = "costs.xlsx"
FILE_FX = "fx_rates.csv"
FILE_FX_XLSX = "fx_rates.xlsx"
FILE_FX_MISSING_EUR = "fx_rates_missing_eur.csv"
FILE_SKU_MAP = "sku_map.csv"
FILE_FEE_REFERENCE = "fee_reference.csv"
FILE_AMAZON_US = "amazon_us_2026-10-01_2026-10-14.tsv"
FILE_AMAZON_DE = "amazon_de_2026-10-01_2026-10-14.tsv"
FILE_AMAZON_UNBALANCED = "amazon_us_unbalanced.tsv"
FILE_SHOPIFY_1007 = "shopify_payout_2026-10-07.csv"
FILE_SHOPIFY_1021 = "shopify_payout_2026-10-21.csv"
FILE_EXPECTED = "EXPECTED.md"
FILE_README = "README.md"
FILE_MAPPING = "mappings/synthetic_orders.yaml"
FILE_ANOMALIES = "expected/anomalies.json"
FILE_SUMMARY = "expected/summary.json"
FILE_PROFIT_EXPECTED = "expected/profit_expected.csv"

# 匹配率分母不含不平衡夹具。该文件只用于 SETTLEMENT_UNBALANCED。
MATCH_RATE_AMAZON_FILES: tuple[str, ...] = (FILE_AMAZON_US, FILE_AMAZON_DE)
MATCH_RATE_SHOPIFY_FILES: tuple[str, ...] = (FILE_SHOPIFY_1007, FILE_SHOPIFY_1021)

ORDER_COLUMNS: tuple[str, ...] = (
    "order_id",
    "order_item_id",
    "store",
    "platform_sku",
    "qty",
    "order_date",
    "item_price",
    "currency",
)
COST_COLUMNS: tuple[str, ...] = ("内部SKU", "采购单价", "头程单价", "币种", "生效日期")
FX_COLUMNS: tuple[str, ...] = ("月份", "原币", "目标币", "汇率")
SKU_MAP_COLUMNS: tuple[str, ...] = ("店铺", "平台SKU", "内部SKU", "标题")
FEE_REFERENCE_COLUMNS: tuple[str, ...] = (
    "platform_sku",
    "currency",
    "expected_fba_fee_per_unit",
)
