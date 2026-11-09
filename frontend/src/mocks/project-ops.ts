import type {
  BrandRow,
  BundleRow,
  CalendarEventRow,
  CategoryRow,
  ChannelRow,
  CostListRow,
  CurrencyCode,
  ExceptionRow,
  FulfillmentRow,
  ListingListRow,
  LookupOption,
  MappingRow,
  ReturnRow,
  SkuCostPoint,
  SkuDetailView,
  SkuListRow,
  TodoRow,
} from '@/types/domain'
import type { MockDatabase } from '@/types/entities'
import { addMinor, mulQty, toDisplay } from '@/utils/money'

function money(minor: number, currency: CurrencyCode) {
  return toDisplay(minor, currency)
}

function storeOf(db: MockDatabase, id: string) {
  return db.stores.find(item => item.id === id)
}

function skuTitle(db: MockDatabase, internalSku: string) {
  return db.skus.find(item => item.internalSku === internalSku)?.title ?? internalSku
}

function activeStatus(active: boolean) {
  return active ? 'active' : 'disabled'
}

export function projectSkuRows(db: MockDatabase): SkuListRow[] {
  return db.skus.map(sku => ({
    id: sku.id,
    internalSku: sku.internalSku,
    title: sku.title,
    brandName: db.brands.find(item => item.id === sku.brandId)?.name ?? sku.brandId,
    categoryName: db.categories.find(item => item.id === sku.categoryId)?.name ?? sku.categoryId,
    status: activeStatus(sku.active),
    listingCount: db.listings.filter(item => item.skuId === sku.id).length,
  }))
}

export function projectSkuDetail(db: MockDatabase, id: string): SkuDetailView | null {
  const sku = db.skus.find(item => item.id === id)

  if (!sku)
    return null

  const costs: SkuCostPoint[] = db.skuCosts
    .filter(item => item.internalSku === sku.internalSku)
    .sort((left, right) => left.validFrom.localeCompare(right.validFrom))
    .map(item => ({
      id: item.id,
      validFrom: item.validFrom,
      validTo: item.validTo ?? '',
      unitCost: money(item.unitCost, item.currency),
      freight: money(item.freightPerUnit, item.currency),
      currency: item.currency,
    }))

  return {
    id: sku.id,
    internalSku: sku.internalSku,
    title: sku.title,
    titleEn: sku.titleEn,
    brandName: db.brands.find(item => item.id === sku.brandId)?.name ?? sku.brandId,
    brandId: sku.brandId,
    categoryName: db.categories.find(item => item.id === sku.categoryId)?.name ?? sku.categoryId,
    categoryId: sku.categoryId,
    status: activeStatus(sku.active),
    costs,
    profits: db.profitSnapshots
      .filter(item => item.internalSku === sku.internalSku)
      .map(item => ({
        period: item.period,
        storeName: storeOf(db, item.storeId)?.name ?? item.storeId,
        profit: money(item.profit, item.currency),
        currency: item.currency,
      })),
    orders: db.orderLines
      .filter(line => line.internalSku === sku.internalSku)
      .map(line => {
        const order = db.orders.find(item => item.id === line.orderId)

        return {
          id: order?.id ?? line.orderId,
          orderNo: order?.orderNo ?? line.orderId,
          orderedAt: order?.orderedAt.slice(0, 10) ?? '',
          qty: line.qty,
          status: order?.status ?? '',
        }
      }),
    mappings: db.mappings
      .filter(item => item.internalSku === sku.internalSku)
      .map(item => ({
        id: item.id,
        storeName: storeOf(db, item.storeId)?.name ?? item.storeId,
        platformSku: item.platformSku,
        status: item.status,
      })),
  }
}

export function projectCosts(db: MockDatabase): CostListRow[] {
  return db.skuCosts.map(item => ({
    id: item.id,
    internalSku: item.internalSku,
    title: skuTitle(db, item.internalSku),
    validFrom: item.validFrom,
    validTo: item.validTo ?? '',
    unitCost: money(item.unitCost, item.currency),
    freight: money(item.freightPerUnit, item.currency),
    currency: item.currency,
  }))
}

export function projectListings(db: MockDatabase): ListingListRow[] {
  return db.listings.map(item => {
    const store = storeOf(db, item.storeId)
    const sku = db.skus.find(row => row.id === item.skuId)

    return {
      id: item.id,
      storeId: item.storeId,
      storeName: store?.name ?? item.storeId,
      platform: store?.platform ?? '',
      marketplace: store?.marketplace ?? '',
      title: item.title,
      platformListingId: item.platformListingId,
      skuId: item.skuId,
      internalSku: sku?.internalSku ?? item.skuId,
      status: item.status,
      price: money(item.price, item.currency),
      currency: item.currency,
    }
  })
}

export function projectListing(db: MockDatabase, id: string): ListingListRow | null {
  return projectListings(db).find(item => item.id === id) ?? null
}

export function projectCategories(db: MockDatabase): CategoryRow[] {
  return db.categories.map(item => ({
    id: item.id,
    name: item.name,
    parentId: item.parentId ?? '',
    parentName: db.categories.find(row => row.id === item.parentId)?.name ?? '',
    sortNo: item.sortNo,
    status: activeStatus(item.active),
  }))
}

export function projectBrands(db: MockDatabase): BrandRow[] {
  return db.brands.map(item => ({
    id: item.id,
    name: item.name,
    skuCount: db.skus.filter(sku => sku.brandId === item.id).length,
    status: activeStatus(item.active),
  }))
}

export function projectMappings(db: MockDatabase): MappingRow[] {
  return db.mappings.map(item => {
    const store = storeOf(db, item.storeId)

    return {
      id: item.id,
      storeId: item.storeId,
      storeName: store?.name ?? item.storeId,
      platform: store?.platform ?? '',
      platformSku: item.platformSku,
      internalSku: item.internalSku,
      status: item.status,
    }
  })
}

export function projectBundles(db: MockDatabase): BundleRow[] {
  return db.bundles.map(item => ({
    id: item.id,
    parentInternalSku: item.parentInternalSku,
    parentTitle: skuTitle(db, item.parentInternalSku),
    childInternalSku: item.childInternalSku,
    childTitle: skuTitle(db, item.childInternalSku),
    qty: item.qty,
  }))
}

export function projectReturns(db: MockDatabase): ReturnRow[] {
  return db.returns.map(item => {
    const order = db.orders.find(row => row.id === item.orderId)

    return {
      id: item.id,
      orderId: item.orderId,
      orderNo: order?.orderNo ?? item.orderId,
      storeName: storeOf(db, item.storeId)?.name ?? item.storeId,
      amount: money(item.amount, item.currency),
      currency: item.currency,
      postedAt: item.postedAt.slice(0, 10),
      status: item.status,
    }
  })
}

export function projectExceptions(db: MockDatabase): ExceptionRow[] {
  return db.issues.map(item => {
    const order = db.orders.find(row => row.orderNo === item.refNo || row.id === item.refNo)

    return {
      id: item.id,
      code: item.code,
      severity: item.severity,
      storeName: storeOf(db, item.storeId)?.name ?? item.storeId,
      refNo: item.refNo,
      orderId: order?.id ?? '',
      amount: money(item.amount, item.currency),
      currency: item.currency,
      status: item.status,
      summary: item.summary,
    }
  })
}

export function projectChannels(db: MockDatabase): ChannelRow[] {
  const groups = new Map<string, { id: string; platform: string; currency: CurrencyCode; orders: number; sales: number; refunds: number }>()

  for (const order of db.orders) {
    const store = storeOf(db, order.storeId)
    const platform = store?.platform ?? 'Unknown'
    const key = `${platform}-${order.currency}`

    const current = groups.get(key) ?? {
      id: key,
      platform,
      currency: order.currency,
      orders: 0,
      sales: 0,
      refunds: 0,
    }

    const gross = db.orderLines
      .filter(line => line.orderId === order.id)
      .reduce((sum, line) => addMinor(sum, mulQty(line.unitPrice, line.qty)), 0)

    current.orders += 1
    current.sales = addMinor(current.sales, gross)
    current.refunds = addMinor(current.refunds, order.refund)
    groups.set(key, current)
  }

  return [...groups.values()].map(item => ({
    ...item,
    sales: toDisplay(item.sales, item.currency),
    refunds: toDisplay(item.refunds, item.currency),
  }))
}

export function projectFulfillment(db: MockDatabase): FulfillmentRow[] {
  return db.orders.map(order => ({
    id: order.id,
    orderNo: order.orderNo,
    storeName: storeOf(db, order.storeId)?.name ?? order.storeId,
    status: order.status,
    fulfillment: order.fulfillment,
    warehouse: db.warehouses.find(item => item.id === order.warehouseId)?.name ?? order.warehouseId,
    carrier: order.carrierName,
    trackingNo: order.trackingNo,
    shippedAt: order.shippedAt ? order.shippedAt.slice(0, 10) : '',
  }))
}

export function projectTodos(db: MockDatabase): TodoRow[] {
  const rows: TodoRow[] = []

  for (const order of db.purchaseOrders.filter(item => item.status === 'submitted')) {
    rows.push({
      id: `po-${order.id}`,
      kind: 'approval',
      title: order.no,
      detail: '待审批采购单',
      at: order.createdAt.slice(0, 10),
      to: `/procurement/orders/${order.id}`,
    })
  }

  for (const item of db.approvals.filter(row => row.status === 'pending')) {
    rows.push({
      id: `ap-${item.id}`,
      kind: 'approval',
      title: item.title,
      detail: item.summary,
      at: item.submittedAt.slice(0, 10),
      to: '/approvals',
    })
  }

  for (const alert of db.alerts.filter(item => item.status === 'open')) {
    const warehouse = db.warehouses.find(item => item.id === alert.warehouseId)

    rows.push({
      id: alert.id,
      kind: 'alert',
      title: alert.internalSku,
      detail: `${warehouse?.name ?? alert.warehouseId} ${alert.kind === 'stockout' ? '断货' : '低于安全库存'}`,
      at: alert.triggeredAt.slice(0, 10),
      to: '/inventory/alerts',
    })
  }

  for (const issue of db.issues.filter(item => item.status === 'open')) {
    const order = db.orders.find(row => row.orderNo === issue.refNo)

    rows.push({
      id: issue.id,
      kind: 'exception',
      title: issue.refNo || issue.id,
      detail: `${issue.code} ${issue.summary}`,
      at: '',
      to: order ? `/orders/${order.id}` : '/orders/exceptions',
    })
  }

  for (const issue of db.issues.filter(item => item.code === 'UNKNOWN_FEE_TYPE' || item.code === 'DUPLICATE_ROW')) {
    rows.push({
      id: `imp-${issue.id}`,
      kind: 'import',
      title: issue.refNo || issue.id,
      detail: issue.summary,
      at: '',
      to: '/finance/issues',
    })
  }

  return rows
}

export function projectCalendar(db: MockDatabase): CalendarEventRow[] {
  const events: CalendarEventRow[] = []

  for (const order of db.purchaseOrders) {
    events.push({
      id: `arr-${order.id}`,
      title: `到货 ${order.no}`,
      start: order.expectedAt.slice(0, 10),
      kind: 'arrival',
      to: `/procurement/orders/${order.id}`,
    })
  }

  for (const settlement of db.settlements) {
    events.push({
      id: `pay-${settlement.id}`,
      title: `打款 ${settlement.externalId}`,
      start: settlement.periodEnd,
      kind: 'payout',
      to: '/finance/recon',
    })
  }

  for (const order of db.orders.filter(item => item.shippedAt)) {
    events.push({
      id: `ship-${order.id}`,
      title: `发货 ${order.orderNo}`,
      start: order.shippedAt?.slice(0, 10) ?? '',
      kind: 'ship',
      to: `/orders/${order.id}`,
    })
  }

  for (const shipment of db.shipments) {
    if (shipment.departedAt) {
      events.push({
        id: `dep-${shipment.id}`,
        title: `头程发出 ${shipment.no}`,
        start: shipment.departedAt.slice(0, 10),
        kind: 'ship',
        to: `/logistics/shipments/${shipment.id}`,
      })
    }
  }

  return events.filter(item => item.start)
}

export function projectPeriods(db: MockDatabase): string[] {
  return [...new Set(db.orders.map(item => item.orderedAt.slice(0, 7)))].sort()
}

export function projectLookups(db: MockDatabase): {
  skus: LookupOption[]
  brands: LookupOption[]
  categories: LookupOption[]
  stores: LookupOption[]
  orders: LookupOption[]
} {
  return {
    skus: db.skus.map(item => ({ id: item.id, label: `${item.internalSku} ${item.title}` })),
    brands: db.brands.map(item => ({ id: item.id, label: item.name })),
    categories: db.categories.map(item => ({ id: item.id, label: item.name })),
    stores: db.stores.map(item => ({ id: item.id, label: item.name })),
    orders: db.orders
      .filter(item => item.status === 'shipped' || item.status === 'partial_refund')
      .map(item => ({ id: item.id, label: item.orderNo })),
  }
}
