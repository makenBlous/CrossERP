import type { CurrencyCode } from '@/types/domain'
import type { MockDatabase, SalesOrder, SalesOrderLine, SkuCost } from '@/types/entities'
import { type Minor, addMinor, convertMinor, mulQty, percentOf } from '@/utils/money'

export const PROFIT_RULE = 'demo-rule-1'

export const PROFIT_INCLUDED_ORDER_STATUSES = ['shipped', 'partial_refund', 'refunded'] as const
export const PROFIT_SOURCE_ORDER_SCOPE = '利润快照仅计入已发货、部分退款或已退款订单；已付款未发货不计入。'

const PLATFORM_FEE_BPS: Record<string, number> = {
  'Amazon': 1500,
  'Shopify': 340,
  'TikTok Shop': 800,
}

const ADS_BPS = 500

export interface ProfitParts {
  revenue: Minor
  fees: Minor
  refunds: Minor
  cogs: Minor
  freight: Minor
  ads: Minor
  profit: Minor
}

export function costFor(db: MockDatabase, internalSku: string): SkuCost | undefined {
  return db.skuCosts.find(row => row.internalSku === internalSku)
}

export function profitOfLine(
  db: MockDatabase,
  order: SalesOrder,
  line: SalesOrderLine,
  platform: string,
): ProfitParts {
  const gross = mulQty(line.unitPrice, line.qty)

  const orderGross = db.orderLines
    .filter(row => row.orderId === order.id)
    .reduce((sum, row) => addMinor(sum, mulQty(row.unitPrice, row.qty)), 0)

  const refundShare = orderGross === 0 ? 0 : Math.round(order.refund * gross / orderGross)
  const revenue = gross - refundShare
  const fees = percentOf(gross, PLATFORM_FEE_BPS[platform] ?? 1500)
  const ads = percentOf(revenue > 0 ? revenue : 0, ADS_BPS)
  const cost = costFor(db, line.internalSku)
  const cogs = cost ? convertMinor(mulQty(cost.unitCost, line.qty), cost.currency, order.currency) : 0
  const freight = cost ? convertMinor(mulQty(cost.freightPerUnit, line.qty), cost.currency, order.currency) : 0
  const profit = revenue - fees - ads - freight - cogs

  return { revenue, fees, refunds: refundShare, cogs, freight, ads, profit }
}

export function rebuildProfit(db: MockDatabase) {
  db.profitSnapshots = []

  const included = new Set<string>(PROFIT_INCLUDED_ORDER_STATUSES)

  for (const order of db.orders) {
    if (!included.has(order.status))
      continue

    const store = db.stores.find(item => item.id === order.storeId)

    if (!store)
      continue

    const period = order.orderedAt.slice(0, 7)

    for (const line of db.orderLines.filter(row => row.orderId === order.id)) {
      const parts = profitOfLine(db, order, line, store.platform)

      const existing = db.profitSnapshots.find(row =>
        row.period === period && row.internalSku === line.internalSku && row.storeId === order.storeId && row.currency === order.currency,
      )

      if (existing) {
        existing.revenue = addMinor(existing.revenue, parts.revenue)
        existing.fees = addMinor(existing.fees, parts.fees)
        existing.refunds = addMinor(existing.refunds, parts.refunds)
        existing.cogs = addMinor(existing.cogs, parts.cogs)
        existing.freight = addMinor(existing.freight, parts.freight)
        existing.ads = addMinor(existing.ads, parts.ads)
        existing.profit = addMinor(existing.profit, parts.profit)
      }
      else {
        db.profitSnapshots.push({
          id: `pft-${db.profitSnapshots.length + 1}`,
          period,
          internalSku: line.internalSku,
          storeId: order.storeId,
          currency: order.currency as CurrencyCode,
          calcVersion: PROFIT_RULE,
          ...parts,
        })
      }
    }
  }
}
