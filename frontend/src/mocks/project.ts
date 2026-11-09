import type {
  AgentDefinition,
  AgentRun,
  ApprovalItem,
  ChatMessage,
  ChatThread,
  CrmAccount,
  CrmAccountDetail,
  CurrencyCode,
  DashboardPayload,
  InventoryTotals,
  IssueRow,
  OnHandRow,
  OrderDetail,
  OrderFee,
  OrderSummary,
  ProfitRow,
  ReconRun,
  StockAlert,
  Store,
  StoreProfit,
  VoucherRow,
} from '@/types/domain'
import type { MockDatabase, SalesOrder } from '@/types/entities'
import { profitOfLine } from '@/mocks/services/profit'
import { type Minor, addMinor, convertMinor, mulQty, percentRatio, toDisplay } from '@/utils/money'

const ORDER_STATUS_ZH: Record<string, string> = {
  paid: '待发货',
  shipped: '已发货',
  partial_refund: '部分退款',
  refunded: '已退款',
  cancelled: '已取消',
}

const CRM_STATUS_ZH: Record<string, string> = {
  active: '合作中',
  negotiating: '谈判中',
  follow_up: '跟进中',
  converted: '线索转化',
}

function label(map: Record<string, string>, value: string) {
  return map[value] ?? value
}

function utcLabel(value: string) {
  return `${value.slice(0, 16).replace('T', ' ')} UTC`
}

function money(minor: Minor, currency: CurrencyCode) {
  return toDisplay(minor, currency)
}

function storeOf(db: MockDatabase, id: string) {
  return db.stores.find(item => item.id === id)
}

function orderGross(db: MockDatabase, orderId: string) {
  return db.orderLines
    .filter(line => line.orderId === orderId)
    .reduce((sum, line) => addMinor(sum, mulQty(line.unitPrice, line.qty)), 0)
}

export function projectStores(db: MockDatabase): Store[] {
  return db.stores.map(item => ({
    id: item.id,
    name: item.name,
    platform: item.platform,
    marketplace: item.marketplace,
    currency: item.currency,
  }))
}

export function projectOrders(db: MockDatabase): OrderSummary[] {
  return db.orders.map(order => toSummary(db, order))
}

function toSummary(db: MockDatabase, order: SalesOrder): OrderSummary {
  const store = storeOf(db, order.storeId)
  const gross = orderGross(db, order.id)
  const lines = db.orderLines.filter(line => line.orderId === order.id)

  const feeTotal = lines.reduce((sum, line) => {
    const parts = profitOfLine(db, order, line, store?.platform ?? 'Amazon')

    return addMinor(sum, parts.fees)
  }, 0)

  return {
    id: order.id,
    orderNo: order.orderNo,
    storeId: order.storeId,
    storeName: store?.name ?? order.storeId,
    platform: store?.platform ?? '',
    marketplace: store?.marketplace ?? '',
    orderedAt: utcLabel(order.orderedAt),
    status: label(ORDER_STATUS_ZH, order.status),
    statusCode: order.status,
    currency: order.currency,
    itemTotal: money(gross, order.currency),
    feeTotal: money(feeTotal, order.currency),
    refund: money(order.refund, order.currency),
    net: money(gross - feeTotal - order.refund, order.currency),
    fulfillment: order.fulfillment,
  }
}

export function projectOrder(db: MockDatabase, id: string): OrderDetail | null {
  const order = db.orders.find(item => item.id === id)

  if (!order)
    return null

  const store = storeOf(db, order.storeId)
  const summary = toSummary(db, order)
  const lines = db.orderLines.filter(line => line.orderId === order.id)
  const fees: OrderFee[] = []

  for (const line of lines) {
    const parts = profitOfLine(db, order, line, store?.platform ?? 'Amazon')

    fees.push({ type: '平台费', amount: money(parts.fees, order.currency), currency: order.currency })
    fees.push({ type: '广告计提', amount: money(parts.ads, order.currency), currency: order.currency })
    fees.push({ type: '头程', amount: money(parts.freight, order.currency), currency: order.currency })
    fees.push({ type: '成本', amount: money(parts.cogs, order.currency), currency: order.currency })
  }
  const warehouse = db.warehouses.find(item => item.id === order.warehouseId)
  const customer = order.customerId ? db.crmAccounts.find(item => item.id === order.customerId) : undefined
  const opportunity = order.opportunityId ? db.crmOpportunities.find(item => item.id === order.opportunityId) : undefined

  return {
    ...summary,
    buyerRef: order.buyerRef,
    lines: lines.map(line => ({
      sku: line.internalSku,
      title: line.title,
      qty: line.qty,
      unitPrice: money(line.unitPrice, line.currency),
      currency: line.currency,
    })),
    fees,
    shipment: {
      warehouse: warehouse?.name ?? order.warehouseId,
      carrier: order.carrierName,
      trackingNo: order.trackingNo || '待生成',
      shippedAt: order.shippedAt ? utcLabel(order.shippedAt) : '未发货',
    },
    customer: customer ? { id: customer.id, name: customer.name, to: `/crm/accounts/${customer.id}` } : undefined,
    opportunity: opportunity ? { id: opportunity.id, name: opportunity.name, stage: opportunity.stage, to: `/crm/opportunities/${opportunity.id}` } : undefined,
    timeline: db.audit
      .filter(item => item.refId === order.id)
      .map(item => ({ time: utcLabel(item.at), title: item.action, detail: item.summary })),
    related: [
      ...db.stockDocs
        .filter(doc => doc.remark.includes(order.orderNo))
        .map(doc => ({
          id: doc.id,
          type: doc.docType === 'outbound' ? '出库单' : '入库单',
          label: `${doc.docNo} ${doc.remark}`,
          to: doc.docType === 'outbound' ? '/inventory/outbound' : '/inventory/inbound',
        })),
      ...db.returns
        .filter(item => item.orderId === order.id)
        .map(item => ({
          id: item.id,
          type: '退货',
          label: item.id,
          to: '/orders/returns',
        })),
      ...(customer ? [{ id: customer.id, type: '客户', label: customer.name, to: `/crm/accounts/${customer.id}` }] : []),
      ...(opportunity ? [{ id: opportunity.id, type: '商机', label: `${opportunity.name}（${opportunity.stage}）`, to: `/crm/opportunities/${opportunity.id}` }] : []),
      ...(order.shipmentId ? [{ id: order.shipmentId, type: '物流运单', label: order.trackingNo || order.shipmentId, to: `/logistics/shipments/${order.shipmentId}` }] : []),
      ...(order.firstMileBatchId && order.firstMileBatchId !== order.shipmentId ? [{ id: order.firstMileBatchId, type: '头程批次', label: order.firstMileBatchId, to: `/logistics/shipments/${order.firstMileBatchId}` }] : []),
    ],
  }
}

export function projectOnHand(db: MockDatabase): { rows: OnHandRow[]; totals: InventoryTotals } {
  const rows: OnHandRow[] = db.skus.map(sku => {
    const balances = db.balances.filter(item => item.internalSku === sku.internalSku)

    const qtyOf = (kind: 'fba' | 'overseas' | 'domestic') => balances
      .filter(item => db.warehouses.find(warehouse => warehouse.id === item.warehouseId)?.kind === kind)
      .reduce((sum, item) => sum + item.onHand, 0)

    const sold = db.orderLines
      .filter(line => line.internalSku === sku.internalSku)
      .reduce((sum, line) => sum + line.qty, 0)

    const dailySales = Math.round(sold / 150 * 10) / 10
    const available = qtyOf('fba') + qtyOf('overseas') + qtyOf('domestic')
    const coverDays = dailySales === 0 ? 999 : Math.round(available / dailySales)
    const alert: StockAlert = available === 0 ? 'stockout' : coverDays < 21 || available < 20 ? 'low' : 'ok'

    return {
      sku: sku.internalSku,
      name: sku.title,
      fbaQty: qtyOf('fba'),
      fbaWarehouse: 'FBA',
      overseasQty: qtyOf('overseas'),
      overseasWarehouse: '海外仓',
      domesticQty: qtyOf('domestic'),
      domesticWarehouse: '国内仓',
      dailySales,
      coverDays,
      alert,
    }
  })

  return {
    rows,
    totals: {
      fbaQty: rows.reduce((sum, row) => sum + row.fbaQty, 0),
      overseasQty: rows.reduce((sum, row) => sum + row.overseasQty, 0),
      domesticQty: rows.reduce((sum, row) => sum + row.domesticQty, 0),
      lowSku: rows.filter(row => row.alert === 'low').length,
      stockoutSku: rows.filter(row => row.alert === 'stockout').length,
    },
  }
}

function monthKey(value: string) {
  return value.slice(0, 7)
}

export function projectDashboard(db: MockDatabase, storeId = 'all', period = '2026-10'): DashboardPayload {
  const inScope = (id: string) => storeId === 'all' || id === storeId
  const periodOrders = db.orders.filter(order => inScope(order.storeId) && monthKey(order.orderedAt) === period && order.status !== 'cancelled')
  let sales = 0
  let refunds = 0

  for (const order of periodOrders) {
    sales += convertMinor(orderGross(db, order.id), order.currency, 'USD')
    refunds += convertMinor(order.refund, order.currency, 'USD')
  }

  const periodProfit = db.profitSnapshots.filter(row => row.period === period && inScope(row.storeId))
  const profit = periodProfit.reduce((sum, row) => sum + convertMinor(row.profit, row.currency, 'USD'), 0)
  const fees = periodProfit.reduce((sum, row) => sum + convertMinor(row.fees + row.ads, row.currency, 'USD'), 0)

  const trend = ['2026-06', '2026-07', '2026-08', '2026-09', '2026-10', '2026-11'].map(month => {
    const monthOrders = db.orders.filter(order => inScope(order.storeId) && monthKey(order.orderedAt) === month)
    const monthSales = monthOrders.reduce((sum, order) => sum + convertMinor(orderGross(db, order.id), order.currency, 'USD'), 0)

    const monthProfit = db.profitSnapshots
      .filter(row => row.period === month && inScope(row.storeId))
      .reduce((sum, row) => sum + convertMinor(row.profit, row.currency, 'USD'), 0)

    return { month, sales: toDisplay(monthSales, 'USD'), profit: toDisplay(monthProfit, 'USD') }
  })

  const stores = db.stores.filter(store => inScope(store.id)).map(store => {
    const storeOrders = db.orders.filter(order => order.storeId === store.id && monthKey(order.orderedAt) === period)
    const storeSales = storeOrders.reduce((sum, order) => sum + orderGross(db, order.id), 0)

    const storeProfit = db.profitSnapshots
      .filter(row => row.storeId === store.id && row.period === period)
      .reduce((sum, row) => sum + row.profit, 0)

    const run = db.reconRuns.find(item => item.storeId === store.id)

    return {
      storeId: store.id,
      storeName: store.name,
      platform: store.platform,
      marketplace: store.marketplace,
      sales: money(storeSales, store.currency),
      profit: money(storeProfit, store.currency),
      matchRate: run ? percentRatio(run.matched, run.matched + run.unmatched) : 0,
      currency: store.currency,
    }
  })

  const reasonMap = new Map<string, number>()

  for (const issue of db.issues.filter(item => inScope(item.storeId) && item.status === 'open'))
    reasonMap.set(issue.code, (reasonMap.get(issue.code) ?? 0) + 1)

  const runs = db.reconRuns.filter(item => inScope(item.storeId))
  const matched = runs.reduce((sum, item) => sum + item.matched, 0)
  const unmatched = runs.reduce((sum, item) => sum + item.unmatched, 0)

  return {
    periodLabel: `${period}-01 ~ ${period}-31`,
    kpi: {
      sales: toDisplay(sales, 'USD'),
      fees: toDisplay(fees, 'USD'),
      netProfit: toDisplay(profit, 'USD'),
      grossMargin: percentRatio(profit, sales || 1),
      refundRate: percentRatio(refunds, sales || 1),
      matchRate: percentRatio(matched, matched + unmatched),
      openIssues: db.issues.filter(item => inScope(item.storeId) && item.status === 'open').length,
      pendingApprovals: db.approvals.filter(item => item.status === 'pending' && (storeId === 'all' || item.storeId === storeId || item.storeId === null)).length,
      currency: 'USD',
    },
    trend,
    stores,
    reasons: [...reasonMap.entries()].map(([code, count]) => ({ code, count })),
  }
}

export function projectProfit(db: MockDatabase): { rows: ProfitRow[]; stores: StoreProfit[] } {
  const rows: ProfitRow[] = db.profitSnapshots.filter(item => item.period === '2026-10').map(item => {
    const sku = db.skus.find(row => row.internalSku === item.internalSku)
    const store = storeOf(db, item.storeId)

    return {
      sku: item.internalSku,
      name: sku?.title ?? item.internalSku,
      storeId: item.storeId,
      storeName: store?.name ?? item.storeId,
      currency: item.currency,
      revenue: money(item.revenue, item.currency),
      platformFee: money(item.fees, item.currency),
      ads: money(item.ads, item.currency),
      firstMile: money(item.freight, item.currency),
      cost: money(item.cogs, item.currency),
      profit: money(item.profit, item.currency),
    }
  })

  const stores: StoreProfit[] = db.stores.map(store => {
    const mine = db.profitSnapshots.filter(item => item.storeId === store.id && item.period === '2026-10')
    const sum = (pick: (row: typeof mine[number]) => Minor) => mine.reduce((total, row) => addMinor(total, pick(row)), 0)

    return {
      storeId: store.id,
      storeName: store.name,
      currency: store.currency,
      revenue: money(sum(row => row.revenue), store.currency),
      platformFee: money(sum(row => row.fees), store.currency),
      ads: money(sum(row => row.ads), store.currency),
      firstMile: money(sum(row => row.freight), store.currency),
      cost: money(sum(row => row.cogs), store.currency),
      profit: money(sum(row => row.profit), store.currency),
    }
  })

  return { rows, stores }
}

export function projectRecon(db: MockDatabase): ReconRun[] {
  return db.reconRuns.map(item => ({
    id: item.id,
    storeName: storeOf(db, item.storeId)?.name ?? item.storeId,
    period: item.period,
    matched: item.matched,
    unmatched: item.unmatched,
    matchRate: percentRatio(item.matched, item.matched + item.unmatched),
    status: item.status,
    finishedAt: utcLabel(item.finishedAt),
  }))
}

export function projectIssues(db: MockDatabase): IssueRow[] {
  return db.issues.map(item => ({
    id: item.id,
    code: item.code,
    severity: item.severity,
    storeName: storeOf(db, item.storeId)?.name ?? item.storeId,
    refNo: item.refNo,
    amount: item.amount,
    currency: item.currency,
    status: item.status,
    summary: item.summary,
  }))
}

export function projectVouchers(db: MockDatabase): VoucherRow[] {
  return db.vouchers.map(item => ({
    id: item.id,
    no: item.no,
    period: item.period,
    status: item.status,
    debit: item.debit,
    credit: item.credit,
    currency: 'CNY',
    summary: item.summary,
    submitter: item.submitter,
  }))
}

export function projectApprovals(db: MockDatabase): ApprovalItem[] {
  return db.approvals.map(item => ({
    id: item.id,
    title: item.title,
    type: item.type,
    submitter: item.submitter,
    submittedAt: utcLabel(item.submittedAt),
    amount: item.amount,
    currency: item.currency,
    status: item.status,
    summary: item.summary,
    lines: item.lines.map(line => ({
      account: line.account,
      debit: line.debit,
      credit: line.credit,
    })),
    comment: item.comment,
    payloadHash: item.payloadHash,
    timeline: db.audit.filter(event => event.refId === item.id).map(event => ({ at: utcLabel(event.at), title: event.action, detail: event.summary, actor: event.actor })),
  }))
}

export function projectAccounts(db: MockDatabase): CrmAccount[] {
  return db.crmAccounts.map(item => ({
    id: item.id,
    name: item.name,
    type: item.kind,
    country: item.country,
    owner: item.owner,
    currency: item.currency,
    pipeline: money(db.crmOpportunities.filter(row => row.accountId === item.id).reduce((sum, row) => addMinor(sum, row.amount), 0), item.currency),
    orders: db.crmTickets.filter(row => row.accountId === item.id && row.orderNo).length,
    status: label(CRM_STATUS_ZH, item.status),
    tags: item.tags,
  }))
}

export function projectAccount(db: MockDatabase, id: string): CrmAccountDetail | null {
  const account = projectAccounts(db).find(item => item.id === id)
  const raw = db.crmAccounts.find(item => item.id === id)

  if (!account || !raw)
    return null

  return {
    ...account,
    website: raw.website,
    email: raw.email,
    phone: raw.phone,
    note: raw.note,
    contacts: db.crmContacts.filter(item => item.accountId === id).map(item => ({
      name: item.name,
      title: item.title,
      email: item.email,
    })),
    opportunities: db.crmOpportunities.filter(item => item.accountId === id).map(item => ({
      name: item.name,
      amount: money(item.amount, item.currency),
      currency: item.currency,
      stage: item.stage,
    })),
    relatedOrders: db.orders
      .filter(item => item.customerId === id)
      .map(order => {
        return {
          id: order.id,
          orderNo: order.orderNo,
          amount: order ? money(orderGross(db, order.id), order.currency) : 0,
          currency: order?.currency ?? raw.currency,
          date: order.orderedAt.slice(0, 10),
          to: `/orders/${order.id}`,
        }
      }),
    tickets: db.crmTickets.filter(item => item.accountId === id).map(item => ({
      id: item.id,
      subject: item.subject,
      status: item.status === 'open' ? '处理中' : item.status,
    })),
  }
}

export function projectAgentDefinitions(db: MockDatabase): AgentDefinition[] {
  return db.agentDefinitions.map(item => ({
    id: item.id,
    name: item.name,
    duty: item.duty,
    model: item.model,
    status: item.status,
    source: item.source,
    tools: item.tools,
    storeScope: item.storeScope,
  }))
}

export function projectAgentRuns(db: MockDatabase): AgentRun[] {
  return db.agentRuns.map(item => ({ ...item }))
}

export function projectChat(db: MockDatabase): { threads: ChatThread[]; messages: ChatMessage[] } {
  return {
    threads: db.threads.map(item => ({ id: item.id, title: item.title, updatedAt: item.updatedAt })),
    messages: db.messages.filter(item => item.threadId === 'th-1').map(item => ({
      id: item.id,
      role: item.role,
      text: item.text,
      toolCall: item.toolName
        ? { name: item.toolName, args: {}, summary: item.toolSummary ?? '' }
        : undefined,
    })),
  }
}
