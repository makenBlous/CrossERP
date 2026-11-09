import type {
  AlertRow,
  BalanceRow,
  CarrierRow,
  CurrencyCode,
  FreightCheckRow,
  MovementRow,
  PurchaseOrderDetailView,
  PurchaseOrderRow,
  PurchaseReturnRow,
  RateCardRow,
  ReceiptRow,
  RelatedDoc,
  ShipmentDetailView,
  ShipmentRow,
  StatementRow,
  StockDocDetail,
  StockDocRow,
  SupplierDetailView,
  SupplierRow,
  SupplyLookups,
  TimelineItem,
  TrackingRow,
  WarehouseRow,
} from '@/types/domain'
import type { MockDatabase, PurchaseOrder } from '@/types/entities'
import { addMinor, mulQty, toDisplay } from '@/utils/money'

function warehouseName(db: MockDatabase, id: string | null) {
  if (!id)
    return ''

  return db.warehouses.find(item => item.id === id)?.name ?? id
}

function supplierName(db: MockDatabase, id: string) {
  return db.suppliers.find(item => item.id === id)?.name ?? id
}

function skuTitle(db: MockDatabase, internalSku: string) {
  return db.skus.find(item => item.internalSku === internalSku)?.title ?? internalSku
}

function show(amount: number, currency: CurrencyCode) {
  return toDisplay(amount, currency)
}

function day(value: string | null) {
  return value ? value.slice(0, 10) : ''
}

function poAmount(db: MockDatabase, purchaseOrderId: string) {
  return db.purchaseOrderLines
    .filter(line => line.purchaseOrderId === purchaseOrderId)
    .reduce((sum, line) => addMinor(sum, mulQty(line.unitCost, line.qty)), 0)
}

export function auditTimeline(db: MockDatabase, refId: string): TimelineItem[] {
  return db.audit
    .filter(item => item.refId === refId)
    .map(item => ({
      id: item.id,
      at: item.at.slice(0, 16).replace('T', ' '),
      title: item.action,
      detail: item.summary,
      actor: item.actor,
    }))
}

export function projectWarehouses(db: MockDatabase): WarehouseRow[] {
  return db.warehouses.map(item => ({
    id: item.id,
    code: item.code,
    name: item.name,
    kind: item.kind,
    country: item.country,
    status: item.active ? 'active' : 'disabled',
  }))
}

export function projectBalances(db: MockDatabase, kind?: 'fba' | 'overseas' | 'domestic'): BalanceRow[] {
  return db.balances
    .map(item => {
      const warehouse = db.warehouses.find(row => row.id === item.warehouseId)

      return {
        id: item.id,
        warehouseId: item.warehouseId,
        warehouseName: warehouse?.name ?? item.warehouseId,
        kind: warehouse?.kind ?? '',
        internalSku: item.internalSku,
        title: skuTitle(db, item.internalSku),
        onHand: item.onHand,
        reserved: item.reserved,
        inTransit: item.inTransit,
        unfulfillable: item.unfulfillable,
        available: item.onHand - item.reserved,
      }
    })
    .filter(item => !kind || item.kind === kind)
}

export function projectMovements(db: MockDatabase): MovementRow[] {
  return db.movements.map(item => ({
    id: item.id,
    occurredAt: day(item.occurredAt),
    warehouseName: warehouseName(db, item.warehouseId),
    internalSku: item.internalSku,
    qtyDelta: item.qtyDelta,
    inTransitDelta: item.inTransitDelta,
    reason: item.reason,
    refType: item.refType,
    refId: item.refId,
    createdBy: item.createdBy,
  }))
}

function docRow(db: MockDatabase, doc: MockDatabase['stockDocs'][number]): StockDocRow {
  const lines = db.stockDocLines.filter(line => line.docId === doc.id)

  return {
    id: doc.id,
    docNo: doc.docNo,
    docType: doc.docType,
    warehouseId: doc.warehouseId,
    warehouseName: warehouseName(db, doc.warehouseId),
    toWarehouseId: doc.toWarehouseId ?? '',
    toWarehouseName: warehouseName(db, doc.toWarehouseId),
    status: doc.status,
    remark: doc.remark,
    createdBy: doc.createdBy,
    createdAt: day(doc.createdAt),
    lineSummary: lines.map(line => `${line.internalSku} × ${line.qtyExpected}`).join('；'),
  }
}

export function projectStockDocs(db: MockDatabase, docType: string): StockDocRow[] {
  return db.stockDocs.filter(item => item.docType === docType).map(item => docRow(db, item))
}

export function projectStockDoc(db: MockDatabase, id: string): StockDocDetail | null {
  const doc = db.stockDocs.find(item => item.id === id)

  if (!doc)
    return null

  const lines = db.stockDocLines.filter(line => line.docId === doc.id).map(line => {
    const balance = db.balances.find(item => item.warehouseId === doc.warehouseId && item.internalSku === line.internalSku)
    const bookQty = balance?.onHand ?? 0

    return {
      id: line.id,
      internalSku: line.internalSku,
      qtyExpected: line.qtyExpected,
      qtyActual: line.qtyActual,
      variance: line.qtyActual - (doc.docType === 'count' && doc.status === 'draft' ? bookQty : line.qtyExpected),
      bookQty,
    }
  })

  const related: RelatedDoc[] = []
  const order = db.orders.find(item => doc.remark.includes(item.orderNo))

  if (order)
    related.push({ id: order.id, type: '订单', label: order.orderNo, to: `/orders/${order.id}` })

  return {
    ...docRow(db, doc),
    lines,
    timeline: auditTimeline(db, doc.id),
    related,
  }
}

export function projectAlerts(db: MockDatabase): AlertRow[] {
  return db.alerts.map(item => {
    const balance = db.balances.find(row => row.warehouseId === item.warehouseId && row.internalSku === item.internalSku)

    return {
      id: item.id,
      warehouseId: item.warehouseId,
      warehouseName: warehouseName(db, item.warehouseId),
      internalSku: item.internalSku,
      kind: item.kind,
      threshold: item.threshold,
      onHand: balance?.onHand ?? 0,
      triggeredAt: day(item.triggeredAt),
      status: item.status,
    }
  })
}

export function projectSuppliers(db: MockDatabase): SupplierRow[] {
  return db.suppliers.map(item => {
    const contact = db.supplierContacts.find(row => row.supplierId === item.id)

    return {
      id: item.id,
      name: item.name,
      country: item.country,
      currency: item.currency,
      status: item.status,
      contact: contact ? `${contact.name} ${contact.email}` : '',
      openPo: db.purchaseOrders.filter(order => order.supplierId === item.id && order.status !== 'received' && order.status !== 'cancelled').length,
    }
  })
}

function orderView(db: MockDatabase, order: PurchaseOrder) {
  return {
    id: order.id,
    no: order.no,
    status: order.status,
    expectedAt: day(order.expectedAt),
    amount: show(poAmount(db, order.id), order.currency),
    currency: order.currency,
  }
}

export function projectSupplier(db: MockDatabase, id: string): SupplierDetailView | null {
  const supplier = db.suppliers.find(item => item.id === id)

  if (!supplier)
    return null

  const invoices = db.apInvoices.filter(item => item.supplierId === supplier.id && item.status !== 'paid')
  const apBalance = invoices.reduce((sum, item) => addMinor(sum, item.amount), 0)

  return {
    id: supplier.id,
    name: supplier.name,
    country: supplier.country,
    currency: supplier.currency,
    status: supplier.status,
    remark: supplier.remark,
    contacts: db.supplierContacts.filter(item => item.supplierId === supplier.id),
    orders: db.purchaseOrders.filter(item => item.supplierId === supplier.id).map(item => orderView(db, item)),
    apBalance: show(apBalance, supplier.currency),
    apCurrency: supplier.currency,
    timeline: auditTimeline(db, supplier.id),
  }
}

export function projectPurchaseOrders(db: MockDatabase): PurchaseOrderRow[] {
  return db.purchaseOrders.map(item => ({
    id: item.id,
    no: item.no,
    supplierId: item.supplierId,
    supplierName: supplierName(db, item.supplierId),
    status: item.status,
    currency: item.currency,
    expectedAt: day(item.expectedAt),
    amount: show(poAmount(db, item.id), item.currency),
    createdAt: day(item.createdAt),
  }))
}

export function projectPurchaseOrder(db: MockDatabase, id: string): PurchaseOrderDetailView | null {
  const order = db.purchaseOrders.find(item => item.id === id)

  if (!order)
    return null

  const receipts = db.receipts.filter(item => item.purchaseOrderId === order.id)

  const related: RelatedDoc[] = receipts.map(item => ({
    id: item.id,
    type: '收货',
    label: item.no,
    to: '/procurement/receipts',
  }))

  for (const doc of db.stockDocs.filter(item => item.remark.includes(order.no))) {
    related.push({
      id: doc.id,
      type: '入库单',
      label: doc.docNo,
      to: '/inventory/inbound',
    })
  }

  const summary = projectPurchaseOrders(db).find(item => item.id === id)

  if (!summary)
    return null

  return {
    ...summary,
    lines: db.purchaseOrderLines.filter(line => line.purchaseOrderId === order.id).map(line => ({
      id: line.id,
      internalSku: line.internalSku,
      qty: line.qty,
      receivedQty: line.receivedQty,
      unitCost: show(line.unitCost, line.currency),
      currency: line.currency,
      amount: show(mulQty(line.unitCost, line.qty), line.currency),
    })),
    receipts: receipts.map(item => ({
      id: item.id,
      no: item.no,
      warehouseName: warehouseName(db, item.warehouseId),
      receivedAt: day(item.receivedAt),
      qty: db.receiptLines.filter(line => line.receiptId === item.id).reduce((sum, line) => sum + line.qty, 0),
      status: item.status,
    })),
    timeline: auditTimeline(db, order.id),
    related,
  }
}

export function projectReceipts(db: MockDatabase): ReceiptRow[] {
  return db.receipts.map(item => {
    const order = db.purchaseOrders.find(row => row.id === item.purchaseOrderId)
    const qty = db.receiptLines.filter(line => line.receiptId === item.id).reduce((sum, line) => sum + line.qty, 0)

    const orderedQty = order
      ? db.purchaseOrderLines.filter(line => line.purchaseOrderId === order.id).reduce((sum, line) => sum + line.qty, 0)
      : qty

    return {
      id: item.id,
      no: item.no,
      purchaseOrderId: item.purchaseOrderId,
      purchaseOrderNo: order?.no ?? item.purchaseOrderId,
      warehouseName: warehouseName(db, item.warehouseId),
      receivedAt: day(item.receivedAt),
      status: item.status,
      qty,
      orderedQty,
      variance: qty - orderedQty,
    }
  })
}

export function projectPurchaseReturns(db: MockDatabase): PurchaseReturnRow[] {
  return db.purchaseReturns.map(item => ({
    id: item.id,
    no: item.no,
    supplierId: item.supplierId,
    supplierName: supplierName(db, item.supplierId),
    purchaseOrderId: item.purchaseOrderId,
    purchaseOrderNo: db.purchaseOrders.find(order => order.id === item.purchaseOrderId)?.no ?? item.purchaseOrderId,
    status: item.status,
    currency: item.currency,
    amount: show(item.amount, item.currency),
  }))
}

export function projectStatements(db: MockDatabase): StatementRow[] {
  return db.statements.map(item => {
    const orders = db.purchaseOrders.filter(order => order.supplierId === item.supplierId && order.expectedAt.slice(0, 7) === item.period)
    let received = 0

    for (const order of orders) {
      for (const line of db.purchaseOrderLines.filter(row => row.purchaseOrderId === order.id))
        received = addMinor(received, mulQty(line.unitCost, line.receivedQty))
    }

    const paid = db.apInvoices
      .filter(invoice => invoice.supplierId === item.supplierId && invoice.status === 'paid')
      .reduce((sum, invoice) => addMinor(sum, invoice.amount), 0)

    return {
      id: item.id,
      no: item.no,
      supplierId: item.supplierId,
      supplierName: supplierName(db, item.supplierId),
      period: item.period,
      status: item.status,
      currency: item.currency,
      amount: show(item.amount, item.currency),
      receivedAmount: show(received, item.currency),
      paidAmount: show(paid, item.currency),
      variance: show(item.amount - received, item.currency),
    }
  })
}

function shipmentRow(db: MockDatabase, item: MockDatabase['shipments'][number]): ShipmentRow {
  const lines = db.shipmentLines.filter(line => line.shipmentId === item.id)

  return {
    id: item.id,
    no: item.no,
    carrierId: item.carrierId,
    carrierName: db.carriers.find(carrier => carrier.id === item.carrierId)?.name ?? item.carrierId,
    fromName: warehouseName(db, item.warehouseFrom),
    toName: warehouseName(db, item.warehouseTo),
    status: item.status,
    departedAt: day(item.departedAt),
    arrivedAt: day(item.arrivedAt),
    skuSummary: lines.map(line => `${line.internalSku} × ${line.qty}`).join('；'),
    containerNo: item.containerNo ?? '',
  }
}

export function projectShipments(db: MockDatabase): ShipmentRow[] {
  return db.shipments.map(item => shipmentRow(db, item))
}

export function projectShipment(db: MockDatabase, id: string): ShipmentDetailView | null {
  const shipment = db.shipments.find(item => item.id === id)

  if (!shipment)
    return null

  const inbound = db.stockDocs.find(item => item.remark.includes(shipment.no))

  return {
    ...shipmentRow(db, shipment),
    warehouseFrom: shipment.warehouseFrom,
    warehouseTo: shipment.warehouseTo,
    volumetricKg: shipment.volumetricKg ?? '',
    lines: db.shipmentLines.filter(line => line.shipmentId === shipment.id),
    charges: db.shipmentCharges.filter(item => item.shipmentId === shipment.id).map(item => ({
      id: item.id,
      chargeType: item.chargeType,
      amount: show(item.amount, item.currency),
      currency: item.currency,
    })),
    tracking: db.tracking.filter(item => item.shipmentId === shipment.id).map(item => ({
      id: item.id,
      occurredAt: item.occurredAt.slice(0, 16).replace('T', ' '),
      description: item.description,
    })),
    timeline: auditTimeline(db, shipment.id),
    related: inbound
      ? [{ id: inbound.id, type: '入库单', label: inbound.docNo, to: '/inventory/inbound' }]
      : [],
  }
}

export function projectCarriers(db: MockDatabase): CarrierRow[] {
  return db.carriers.map(item => ({
    id: item.id,
    name: item.name,
    status: item.active ? 'active' : 'disabled',
    rateCount: db.rateCards.filter(rate => rate.carrierId === item.id).length,
  }))
}

export function projectRateCards(db: MockDatabase): RateCardRow[] {
  return db.rateCards.map(item => ({
    id: item.id,
    carrierId: item.carrierId,
    carrierName: db.carriers.find(carrier => carrier.id === item.carrierId)?.name ?? item.carrierId,
    dest: item.dest,
    unit: item.unit,
    price: show(item.price, item.currency),
    currency: item.currency,
    validFrom: item.validFrom,
    validTo: item.validTo ?? '',
  }))
}

export function projectTracking(db: MockDatabase): TrackingRow[] {
  return db.tracking.map(item => {
    const shipment = db.shipments.find(row => row.id === item.shipmentId)

    return {
      id: item.id,
      shipmentId: item.shipmentId,
      shipmentNo: shipment?.no ?? item.shipmentId,
      occurredAt: item.occurredAt.slice(0, 16).replace('T', ' '),
      description: item.description,
      status: shipment?.status ?? '',
    }
  })
}

export function projectFreightChecks(db: MockDatabase): FreightCheckRow[] {
  return db.freightChecks.map(item => ({
    id: item.id,
    shipmentId: item.shipmentId,
    shipmentNo: db.shipments.find(row => row.id === item.shipmentId)?.no ?? item.shipmentId,
    billAmount: show(item.billAmount, item.currency),
    estimateAmount: show(item.estimateAmount, item.currency),
    currency: item.currency,
    variance: show(item.variance, item.currency),
    status: item.status,
  }))
}

export function projectSupplyLookups(db: MockDatabase): SupplyLookups {
  return {
    skus: db.skus.map(item => ({ id: item.internalSku, label: `${item.internalSku} ${item.title}` })),
    suppliers: db.suppliers.map(item => ({ id: item.id, label: item.name })),
    warehouses: db.warehouses.map(item => ({ id: item.id, label: `${item.name} (${item.kind})` })),
    carriers: db.carriers.map(item => ({ id: item.id, label: item.name })),
    purchaseOrders: db.purchaseOrders.map(item => ({ id: item.id, label: item.no })),
  }
}
