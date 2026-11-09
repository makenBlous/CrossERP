import { addAgentModuleSeed } from './agent-module'
import type { CurrencyCode, IssueCode } from '@/types/domain'
import type { Actor, MockDatabase, Platform, Shop } from '@/types/entities'
import { submitSuggestion } from '@/mocks/services/approvals'
import { nextId } from '@/mocks/services/ids'
import { applyMovement } from '@/mocks/services/inventory'
import { arriveShipment, departShipment } from '@/mocks/services/logistics'
import { shipSalesOrder } from '@/mocks/services/orders'
import { approvePurchaseOrder, receivePurchaseOrder, submitPurchaseOrder } from '@/mocks/services/procurement'
import { rebuildProfit } from '@/mocks/services/profit'
import { seedAds } from '@/mocks/seed/ads'
import { seedFinance } from '@/mocks/seed/finance'
import { type Minor, addMinor, convertMinor, minorFromDecimal, mulQty } from '@/utils/money'

const SEED = 20261109
const VERSION = 3

function actor(name: string, role: Actor['role'], at: string): Actor {
  return { userId: `demo-${role}`, name, role, at }
}

function iso(month: number, day: number, hour: number) {
  return `2026-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}T${String(hour).padStart(2, '0')}:00:00.000Z`
}

function emptyDb(): MockDatabase {
  return {
    meta: { version: VERSION, seed: SEED, seq: 0, generatedAt: '2026-11-09T00:00:00.000Z' },
    company: { id: 'co-northwind', name: 'Northwind Outdoor', currency: 'USD' },
    stores: [],
    brands: [],
    categories: [],
    skus: [],
    listings: [],
    mappings: [],
    bundles: [],
    skuCosts: [],
    fxRates: [],
    orders: [],
    orderLines: [],
    returns: [],
    warehouses: [],
    balances: [],
    movements: [],
    stockDocs: [],
    stockDocLines: [],
    alerts: [],
    suppliers: [],
    supplierContacts: [],
    purchaseOrders: [],
    purchaseOrderLines: [],
    receipts: [],
    receiptLines: [],
    purchaseReturns: [],
    statements: [],
    carriers: [],
    rateCards: [],
    shipments: [],
    shipmentLines: [],
    shipmentCharges: [],
    tracking: [],
    freightChecks: [],
    settlements: [],
    reconRuns: [],
    issues: [],
    vouchers: [],
    profitSnapshots: [],
    approvals: [],
    crmAccounts: [],
    crmContacts: [],
    crmOpportunities: [],
    crmTickets: [],
    agentDefinitions: [],
    agentTools: [],
    agentRuns: [],
    threads: [],
    messages: [],
    audit: [],
    accounts: [],
    adsCampaigns: [],
    arInvoices: [],
    apInvoices: [],
    knowledgeBases: [],
    deerflow: {
      id: 'df-local',
      baseUrl: 'http://127.0.0.1:2026',
      enabled: false,
      lastOkAt: null,
      lastError: '',
      configRef: 'local-vault:deerflow',
    },
    finance2: { imports: [], feeMaps: [], columnMaps: [], exports: [], clearing: [] },
    ads: { imports: [], allocations: [] },
    crmLeads: [],
    crmActivities: [],
    crmReviews: [],
    crmTicketMessages: [],
    roleOverrides: [],
    adminIntegrations: [],
    adminModules: [],
    adminDicts: [],
    adminNotifications: [],
    adminSettings: [],
    accountTokens: [],
    accountSessions: [],
  }
}

const BASES = [
  ['TENT-2P', '双人帐篷', '2P tent', '帐篷', '186.0000', '22.5000'],
  ['TENT-4P', '四人帐篷', '4P tent', '帐篷', '268.0000', '31.0000'],
  ['STOVE', '钛合金炉头', 'Titanium stove', '炉具', '46.0000', '4.8000'],
  ['SLEEP', '羽绒睡袋', 'Down sleeping bag', '睡眠', '92.0000', '8.6000'],
  ['LAMP', '营地灯', 'Camp lantern', '照明', '28.0000', '3.2000'],
  ['BOTTLE', '钛杯', 'Titanium cup', '水具', '18.5000', '2.4000'],
  ['MAT', '防潮垫', 'Sleeping pad', '垫子', '36.0000', '5.1000'],
  ['PACK', '徒步背包', 'Hiking pack', '背包', '74.0000', '9.4000'],
] as const

const COLORS = [
  ['OLV', '橄榄绿', 'olive'],
  ['SND', '沙色', 'sand'],
  ['BLK', '黑色', 'black'],
  ['NVY', '海军蓝', 'navy'],
  ['RED', '赤陶红', 'terracotta'],
] as const

const BRANDS = ['Northwind', 'RidgeLine', 'CampArc', 'Fieldnote', 'Harbor', 'Kite']
const CATEGORIES = ['帐篷', '炉具', '睡眠', '照明', '水具', '垫子', '背包', '配件']

function addMasters(db: MockDatabase) {
  const stores: Array<[string, string, Platform, string, string, CurrencyCode]> = [
    ['amz-us', 'Northwind Outdoor US', 'Amazon', 'US', 'US', 'USD'],
    ['amz-uk', 'Northwind Outdoor UK', 'Amazon', 'UK', 'GB', 'GBP'],
    ['amz-de', 'Northwind Outdoor DE', 'Amazon', 'DE', 'DE', 'EUR'],
    ['amz-jp', 'Northwind Outdoor JP', 'Amazon', 'JP', 'JP', 'JPY'],
    ['shopify', 'northwind-outdoor.com', 'Shopify', '独立站', 'US', 'USD'],
    ['tiktok-us', 'Northwind TikTok US', 'TikTok Shop', 'US', 'US', 'USD'],
  ]

  db.stores = stores.map(item => ({
    id: item[0],
    companyId: db.company.id,
    name: item[1],
    platform: item[2],
    marketplace: item[3],
    country: item[4],
    currency: item[5],
  }))
  db.brands = BRANDS.map((name, index) => ({ id: `br-${index + 1}`, name, active: true }))
  db.categories = CATEGORIES.map((name, index) => ({
    id: `cat-${index + 1}`,
    parentId: null,
    name,
    sortNo: index + 1,
    active: true,
  }))
  BASES.forEach((base, baseIndex) => {
    COLORS.forEach((color, colorIndex) => {
      const code = `NW-${base[0]}-${color[0]}`
      const category = db.categories.find(item => item.name === base[3])

      db.skus.push({
        id: `sku-${code}`,
        internalSku: code,
        title: `${base[1]} ${color[1]}`,
        titleEn: `${base[2]} ${color[2]}`,
        brandId: db.brands[(baseIndex + colorIndex) % db.brands.length].id,
        categoryId: category?.id ?? db.categories[0].id,
        active: true,
      })
      db.skuCosts.push({
        id: `cost-${code}`,
        internalSku: code,
        validFrom: '2026-01-01',
        validTo: null,
        unitCost: minorFromDecimal(base[4]),
        currency: 'CNY',
        freightPerUnit: minorFromDecimal(base[5]),
      })
    })
  })
  db.bundles = [
    { id: 'bun-1', parentInternalSku: 'NW-TENT-2P-OLV', childInternalSku: 'NW-MAT-OLV', qty: 1 },
    { id: 'bun-2', parentInternalSku: 'NW-TENT-2P-OLV', childInternalSku: 'NW-LAMP-OLV', qty: 1 },
    { id: 'bun-3', parentInternalSku: 'NW-PACK-BLK', childInternalSku: 'NW-BOTTLE-BLK', qty: 1 },
    { id: 'bun-4', parentInternalSku: 'NW-SLEEP-NVY', childInternalSku: 'NW-MAT-NVY', qty: 1 },
  ]

  const fx: Array<[CurrencyCode, string]> = [
    ['EUR', '1.08000000'],
    ['GBP', '1.27000000'],
    ['CNY', '0.14000000'],
    ['JPY', '0.00670000'],
  ]

  db.fxRates = fx.map((item, index) => ({
    id: `fx-${index + 1}`,
    period: '2026-10',
    fromCcy: item[0],
    toCcy: 'USD',
    rate: item[1],
    source: '演示月汇率',
  }))
}

function addWarehouses(db: MockDatabase) {
  const rows: Array<[string, string, string, 'fba' | 'overseas' | 'domestic', string, string | null]> = [
    ['wh-fba-us', 'FBA-US', '亚马逊 FBA 美国', 'fba', 'US', 'amz-us'],
    ['wh-fba-uk', 'FBA-UK', '亚马逊 FBA 英国', 'fba', 'GB', 'amz-uk'],
    ['wh-fba-de', 'FBA-DE', '亚马逊 FBA 德国', 'fba', 'DE', 'amz-de'],
    ['wh-fba-jp', 'FBA-JP', '亚马逊 FBA 日本', 'fba', 'JP', 'amz-jp'],
    ['wh-os-us', 'OS-LAX', '洛杉矶海外仓', 'overseas', 'US', null],
    ['wh-os-de', 'OS-HAM', '汉堡海外仓', 'overseas', 'DE', null],
    ['wh-cn-sz', 'CN-SZ', '深圳备货仓', 'domestic', 'CN', null],
    ['wh-cn-nb', 'CN-NB', '宁波备货仓', 'domestic', 'CN', null],
  ]

  db.warehouses = rows.map(item => ({
    id: item[0],
    code: item[1],
    name: item[2],
    kind: item[3],
    country: item[4],
    storeId: item[5],
    active: true,
  }))

  const opener = actor('系统', 'admin', iso(1, 2, 1))

  for (const warehouse of db.warehouses) {
    const opening = warehouse.kind === 'domestic' ? 180 : warehouse.kind === 'overseas' ? 60 : 80

    for (const sku of db.skus) {
      applyMovement(db, {
        warehouseId: warehouse.id,
        internalSku: sku.internalSku,
        onHandDelta: opening,
        inTransitDelta: 0,
        reason: 'opening',
        refType: 'seed',
        refId: 'opening',
        actor: opener,
      })
    }
  }
}

function listingPrice(cost: Minor, currency: CurrencyCode): Minor {
  const usd = convertMinor(mulQty(cost, 1), 'CNY', 'USD')
  const retailUsd = Math.round(usd * 24 / 10)

  return convertMinor(retailUsd, 'USD', currency)
}

function addListings(db: MockDatabase) {
  db.stores.forEach((store, storeIndex) => {
    db.skus.forEach((sku, skuIndex) => {
      if ((skuIndex + storeIndex) % 3 !== 0)
        return

      const cost = db.skuCosts.find(item => item.internalSku === sku.internalSku)
      const price = listingPrice(cost?.unitCost ?? minorFromDecimal('20'), store.currency)

      db.listings.push({
        id: `lst-${store.id}-${sku.internalSku}`,
        storeId: store.id,
        skuId: sku.id,
        platformListingId: `${store.marketplace}-${sku.internalSku}`,
        title: sku.title,
        status: 'active',
        price,
        currency: store.currency,
      })
      db.mappings.push({
        id: `map-${store.id}-${sku.internalSku}`,
        storeId: store.id,
        platformSku: `${store.marketplace}-${sku.internalSku}`,
        internalSku: sku.internalSku,
        status: 'confirmed',
      })
    })
  })
}

function addSuppliers(db: MockDatabase) {
  const names = [
    ['sup-01', '义乌远足户外商贸', 'CN', 'CNY'],
    ['sup-02', '宁波海港露营', 'CN', 'CNY'],
    ['sup-03', '深圳钛制品厂', 'CN', 'CNY'],
    ['sup-04', '杭州睡袋工坊', 'CN', 'CNY'],
    ['sup-05', '青岛箱包厂', 'CN', 'CNY'],
    ['sup-06', '厦门灯具厂', 'CN', 'CNY'],
    ['sup-07', 'Osaka Field Gear', 'JP', 'JPY'],
    ['sup-08', 'Hamburg Textile GmbH', 'DE', 'EUR'],
    ['sup-09', 'Portland Stitch Co.', 'US', 'USD'],
    ['sup-10', 'Manchester Canvas Ltd', 'GB', 'GBP'],
  ] as const

  names.forEach(item => {
    db.suppliers.push({
      id: item[0],
      name: item[1],
      country: item[2],
      currency: item[3],
      status: item[0] === 'sup-10' ? 'paused' : 'active',
      remark: '演示供应商',
    })
    db.supplierContacts.push({
      id: `sc-${item[0]}`,
      supplierId: item[0],
      name: '采购联系人',
      email: `${item[0]}@supplier.example`,
      phone: '+00 0000 0000',
    })
  })
  db.carriers = [
    { id: 'car-01', name: '远航货代', active: true },
    { id: 'car-02', name: '北欧海运', active: true },
    { id: 'car-03', name: '太平洋空运', active: true },
    { id: 'car-04', name: '岛内卡车', active: true },
  ]
  db.rateCards = db.carriers.map((carrier, index) => ({
    id: `rate-${index + 1}`,
    carrierId: carrier.id,
    dest: index % 2 === 0 ? 'US' : 'DE',
    unit: 'kg',
    price: minorFromDecimal(index % 2 === 0 ? '6.8000' : '5.4000'),
    currency: 'CNY' as const,
    validFrom: '2026-01-01',
    validTo: null,
  }))
}

function createPurchase(db: MockDatabase, index: number, supplierId: string, at: string) {
  const poId = nextId(db, 'po')
  const supplier = db.suppliers.find(item => item.id === supplierId)

  db.purchaseOrders.push({
    id: poId,
    no: `PO-2026-${String(index + 1).padStart(3, '0')}`,
    supplierId,
    status: 'draft',
    currency: supplier?.currency ?? 'CNY',
    expectedAt: iso(10, 20 + (index % 8), 8),
    createdBy: '林夏',
    createdAt: at,
  })

  const sku = db.skus[index % db.skus.length]
  const cost = db.skuCosts.find(item => item.internalSku === sku.internalSku)

  db.purchaseOrderLines.push({
    id: nextId(db, 'pol'),
    purchaseOrderId: poId,
    internalSku: sku.internalSku,
    qty: 40 + (index % 5) * 10,
    receivedQty: 0,
    unitCost: convertMinor(cost?.unitCost ?? minorFromDecimal('20'), 'CNY', supplier?.currency ?? 'CNY'),
    currency: supplier?.currency ?? 'CNY',
  })

  return poId
}

function addPurchases(db: MockDatabase) {
  const maker = actor('林夏', 'operator', iso(9, 2, 3))
  const approver = actor('周衡', 'finance', iso(9, 3, 4))
  const receiver = actor('林夏', 'operator', iso(9, 12, 6))

  for (let index = 0; index < 12; index += 1) {
    const poId = createPurchase(db, index, db.suppliers[index % db.suppliers.length].id, iso(9, 1, 2))

    if (index < 10)
      submitPurchaseOrder(db, poId, maker)
    if (index < 7)
      approvePurchaseOrder(db, poId, approver)
    if (index < 4)
      receivePurchaseOrder(db, poId, index % 2 === 0 ? 'wh-cn-sz' : 'wh-cn-nb', receiver)
  }
  db.purchaseReturns = [
    { id: 'prt-1', no: 'PR-2026-001', supplierId: 'sup-01', purchaseOrderId: db.purchaseOrders[0].id, status: 'draft', currency: 'CNY', amount: minorFromDecimal('1860.0000') },
    { id: 'prt-2', no: 'PR-2026-002', supplierId: 'sup-03', purchaseOrderId: db.purchaseOrders[1].id, status: 'draft', currency: 'CNY', amount: minorFromDecimal('460.0000') },
  ]
  db.statements = [0, 1, 2, 3].map(index => ({
    id: `stm-${index + 1}`,
    no: `ST-2026-10-0${index + 1}`,
    supplierId: db.suppliers[index].id,
    period: '2026-10',
    status: index === 0 ? 'submitted' : 'draft',
    currency: db.suppliers[index].currency,
    amount: minorFromDecimal('12800.0000'),
  }))
}

function addShipments(db: MockDatabase) {
  const planner = actor('林夏', 'operator', iso(9, 18, 2))
  const destinations = ['wh-fba-us', 'wh-fba-uk', 'wh-fba-de', 'wh-fba-jp', 'wh-fba-us', 'wh-fba-de']

  destinations.forEach((dest, index) => {
    const id = nextId(db, 'shp')
    const sku = db.skus[index * 3]

    db.shipments.push({
      id,
      no: `FM-2026-${String(index + 1).padStart(3, '0')}`,
      carrierId: db.carriers[index % db.carriers.length].id,
      warehouseFrom: 'wh-cn-sz',
      warehouseTo: dest,
      status: 'planned',
      departedAt: null,
      arrivedAt: null,
    })
    db.shipmentLines.push({ id: nextId(db, 'spl'), shipmentId: id, internalSku: sku.internalSku, qty: 24 })
    db.shipmentCharges.push({
      id: nextId(db, 'chg'),
      shipmentId: id,
      chargeType: 'freight',
      amount: minorFromDecimal('1680.0000'),
      currency: 'CNY',
    })
    if (index < 4)
      departShipment(db, id, { ...planner, at: iso(9, 20, 8) })
    if (index < 2)
      arriveShipment(db, id, { ...planner, at: iso(10, 8, 9) })
  })
  for (const shipment of db.shipments) {
    const charge = db.shipmentCharges.find(item => item.shipmentId === shipment.id)
    const estimate = minorFromDecimal('1632.0000')
    const bill = charge?.amount ?? estimate

    db.freightChecks.push({
      id: nextId(db, 'frt'),
      shipmentId: shipment.id,
      billAmount: bill,
      estimateAmount: estimate,
      currency: 'CNY',
      variance: bill - estimate,
      status: bill === estimate ? 'matched' : 'variance',
    })
  }
}

function storeWarehouse(store: Shop) {
  if (store.id === 'amz-us')
    return 'wh-fba-us'
  if (store.id === 'amz-uk')
    return 'wh-fba-uk'
  if (store.id === 'amz-de')
    return 'wh-fba-de'
  if (store.id === 'amz-jp')
    return 'wh-fba-jp'
  if (store.id === 'tiktok-us')
    return 'wh-os-us'

  return 'wh-os-us'
}

function addOrders(db: MockDatabase) {
  const plan = [
    ...Array.from({ length: 40 }, () => 'amz-us'),
    ...Array.from({ length: 15 }, () => 'amz-uk'),
    ...Array.from({ length: 15 }, () => 'amz-de'),
    ...Array.from({ length: 10 }, () => 'amz-jp'),
    ...Array.from({ length: 12 }, () => 'shopify'),
    ...Array.from({ length: 8 }, () => 'tiktok-us'),
  ]

  const months = [6, 7, 7, 8, 8, 8, 9, 9, 9, 10, 10, 10, 10, 11]
  const shipper = actor('林夏', 'operator', iso(10, 21, 7))

  plan.forEach((storeId, index) => {
    const store = db.stores.find(item => item.id === storeId)

    if (!store)
      return

    const listings = db.listings.filter(item => item.storeId === storeId)
    const listing = listings[index % listings.length]
    const sku = db.skus.find(item => item.id === listing.skuId)

    if (!sku)
      return

    const month = months[index % months.length]
    const day = (index % 27) + 1
    const orderId = nextId(db, 'ord')

    const orderNo = store.platform === 'Shopify'
      ? `#${10420 + index}`
      : `${110 + (index % 80)}-${1000000 + index * 17}-${2000000 + index * 13}`

    db.orders.push({
      id: orderId,
      storeId,
      orderNo,
      orderedAt: iso(month, day, 8 + (index % 10)),
      buyerRef: `buyer-${index + 1}`,
      status: 'paid',
      currency: store.currency,
      fulfillment: store.platform === 'Amazon' ? 'FBA' : 'Merchant',
      warehouseId: storeWarehouse(store),
      carrierName: store.platform === 'Amazon' ? 'Amazon Logistics' : '远航货代',
      trackingNo: '',
      shippedAt: null,
      refund: 0,
    })
    db.orderLines.push({
      id: nextId(db, 'oln'),
      orderId,
      internalSku: sku.internalSku,
      title: sku.title,
      qty: (index % 3) + 1,
      unitPrice: listing.price,
      currency: store.currency,
    })
    if (index % 11 !== 0)
      shipSalesOrder(db, orderId, { ...shipper, at: iso(month, Math.min(day + 2, 28), 15) })

    if (index % 17 === 0) {
      const order = db.orders.find(item => item.id === orderId)

      if (order && order.status === 'shipped') {
        const line = db.orderLines.find(item => item.orderId === orderId)

        order.refund = line ? mulQty(line.unitPrice, 1) : 0
        order.status = 'partial_refund'
        db.returns.push({
          id: nextId(db, 'rtn'),
          storeId,
          orderId,
          amount: order.refund,
          currency: order.currency,
          postedAt: iso(month, Math.min(day + 5, 28), 11),
          status: 'posted',
        })
      }
    }
  })
  rebuildProfit(db)
}

function addFinance(db: MockDatabase) {
  for (const store of db.stores) {
    const october = db.orders.filter(order => order.storeId === store.id && order.orderedAt.startsWith('2026-10') && order.status !== 'paid')

    const total = october.reduce((sum, order) => {
      const lines = db.orderLines.filter(line => line.orderId === order.id)
      const gross = lines.reduce((inner, line) => addMinor(inner, mulQty(line.unitPrice, line.qty)), 0)

      return addMinor(sum, gross - order.refund)
    }, 0)

    db.settlements.push({
      id: `stl-${store.id}-10`,
      storeId: store.id,
      platform: store.platform,
      externalId: `STL-${store.marketplace}-2026-10`,
      periodStart: '2026-10-01',
      periodEnd: '2026-10-31',
      total,
      currency: store.currency,
      status: 'imported',
    })
    db.reconRuns.push({
      id: `recon-${store.id}-10`,
      storeId: store.id,
      period: '2026-10',
      matched: Math.max(october.length - 1, 0),
      unmatched: october.length === 0 ? 0 : 1,
      status: 'done',
      finishedAt: iso(11, 2, 6),
    })
    db.adsCampaigns.push({
      id: `ads-${store.id}`,
      storeId: store.id,
      name: `${store.marketplace} 秋季活动`,
      status: 'active',
      spend: minorFromDecimal(store.currency === 'JPY' ? '18000' : '420.0000'),
      currency: store.currency,
    })
    db.arInvoices.push({
      id: `ar-${store.id}`,
      storeId: store.id,
      amount: total,
      currency: store.currency,
      status: 'open',
      dueAt: '2026-11-15',
    })
  }
  const codes: IssueCode[] = ['AMOUNT_MISMATCH', 'UNKNOWN_FEE_TYPE', 'DUPLICATE_ROW', 'SETTLEMENT_UNBALANCED']

  const picked = db.stores.flatMap(store => {
    const found = db.orders.find(order => order.storeId === store.id && order.status !== 'paid')

    return found ? [found] : []
  })

  const extra = db.orders.filter(order => order.status !== 'paid' && !picked.includes(order)).slice(0, 6)
  const shipped = [...picked, ...extra]

  shipped.forEach((order, index) => {
    const store = db.stores.find(item => item.id === order.storeId)

    if (!store)
      return

    db.issues.push({
      id: `iss-${index + 1}`,
      code: codes[index % codes.length],
      severity: index % 4 === 0 ? 'high' : index % 3 === 0 ? 'low' : 'medium',
      storeId: store.id,
      refNo: order.orderNo,
      amount: store.currency === 'JPY' ? minorFromDecimal('480') : minorFromDecimal('12.4000'),
      currency: store.currency,
      status: index % 5 === 0 ? 'explained' : 'open',
      summary: '演示异常。金额来自种子，不由模型改写。',
    })
  })
  db.vouchers = [
    { id: 'vch-1', no: '记-2026-10-018', period: '2026-10', status: 'draft', debit: minorFromDecimal('42856.0000'), credit: minorFromDecimal('42856.0000'), currency: 'CNY', summary: '10 月收入与费用草稿', submitter: '林夏' },
    { id: 'vch-2', no: '记-2026-10-019', period: '2026-10', status: 'pending', debit: minorFromDecimal('18640.2000'), credit: minorFromDecimal('18640.2000'), currency: 'CNY', summary: '帐篷成本结转，待财务审批', submitter: '林夏' },
    { id: 'vch-3', no: '记-2026-09-011', period: '2026-09', status: 'posted', debit: minorFromDecimal('96220.0000'), credit: minorFromDecimal('96220.0000'), currency: 'CNY', summary: '9 月利润凭证', submitter: '周衡' },
  ]
  db.approvals.push({
    id: 'apr-voucher-1',
    targetType: 'voucher',
    targetId: 'vch-2',
    title: '10 月帐篷成本结转',
    type: '凭证草稿',
    submitter: '林夏',
    submittedAt: iso(11, 3, 9),
    amount: minorFromDecimal('18640.2000'),
    currency: 'CNY',
    status: 'pending',
    summary: '按生效期成本结转。金额来自系统计算，不是模型改写。',
    storeId: 'amz-us',
    lines: [
      { account: '主营业务成本', debit: minorFromDecimal('18640.2000'), credit: 0 },
      { account: '库存商品', debit: 0, credit: minorFromDecimal('18640.2000') },
    ],
  })

  const firstIssue = db.issues[0]

  if (firstIssue) {
    submitSuggestion(db, {
      title: '结算差额挂账建议',
      summary: `引用异常 ${firstIssue.id}，金额沿用已存储差额。智能体不重算。`,
      amount: firstIssue.currency === 'JPY' ? '480' : '12.4000',
      currency: firstIssue.currency,
      storeId: firstIssue.storeId,
      targetType: 'issue_note',
      targetId: firstIssue.id,
    }, actor('对账解释员', 'operator', iso(11, 4, 2)))
  }
  db.accounts = [
    { code: '6001', name: '主营业务收入', direction: 'credit', active: true },
    { code: '6401', name: '主营业务成本', direction: 'debit', active: true },
    { code: '1405', name: '库存商品', direction: 'debit', active: true },
    { code: '2202', name: '应付账款', direction: 'credit', active: true },
  ]
  db.apInvoices = db.suppliers.slice(0, 4).map((supplier, index) => ({
    id: `ap-${index + 1}`,
    supplierId: supplier.id,
    amount: minorFromDecimal('8600.0000'),
    currency: supplier.currency,
    status: 'open',
    dueAt: '2026-11-30',
  }))
}

function addCrm(db: MockDatabase) {
  const rows = [
    ['acc-alpine', 'Alpine Peak Distributors GmbH', '分销商', '德国', '林夏', 'EUR', 'active'],
    ['acc-ridge', 'Ridge & Co. Ltd', '分销商', '英国', '林夏', 'GBP', 'negotiating'],
    ['acc-summit', 'Summit Trail LLC', '批发客户', '美国', '周衡', 'USD', 'active'],
    ['acc-yiwu', '远足户外商贸', '渠道合作方', '中国', '周衡', 'CNY', 'converted'],
    ['acc-pacific', 'Pacific Outdoor Brokerage', '渠道合作方', '新加坡', '林夏', 'USD', 'follow_up'],
    ['acc-kiso', '木曾户外株式会社', '分销商', '日本', '周衡', 'JPY', 'negotiating'],
    ['acc-elbe', 'Elbe Camp GmbH', '批发客户', '德国', '林夏', 'EUR', 'active'],
    ['acc-cove', 'Cove Retail Co.', '独立站买家', '美国', '周衡', 'USD', 'follow_up'],
  ] as const

  rows.forEach(item => {
    db.crmAccounts.push({
      id: item[0],
      name: item[1],
      kind: item[2],
      country: item[3],
      owner: item[4],
      currency: item[5],
      status: item[6],
      tags: [item[3]],
      website: 'https://example.invalid',
      email: `${item[0]}@buyer.example`,
      phone: '+00 0000 0000',
      note: '客户主档不是平台终端消费者。',
    })
    db.crmContacts.push({
      id: `ctc-${item[0]}`,
      accountId: item[0],
      name: '采购联系人',
      title: '采购',
      email: `${item[0]}@buyer.example`,
    })
    db.crmOpportunities.push({
      id: `opp-${item[0]}`,
      accountId: item[0],
      name: '2027 春季补货',
      amount: minorFromDecimal(item[5] === 'JPY' ? '860000' : '18600.0000'),
      currency: item[5],
      stage: '报价',
    })
  })

  const sample = db.orders.find(order => order.storeId === 'shopify')

  db.crmTickets.push({
    id: 'tkt-1',
    accountId: 'acc-summit',
    subject: '独立站少发一箱',
    status: 'open',
    orderNo: sample?.orderNo ?? null,
  })
  db.crmLeads = [
    { id: 'lead-1', name: 'Mia Chen', company: 'Summit Trail LLC', email: 'mia@summit.example', source: '展会', owner: '周衡', stage: 'qualified', accountId: 'acc-summit', contactId: 'ctc-acc-summit', opportunityId: null, createdAt: '2026-11-02' },
    { id: 'lead-2', name: 'Oliver Smith', company: 'Ridge & Co. Ltd', email: 'oliver@ridge.example', source: '网站表单', owner: '林夏', stage: 'new', accountId: null, contactId: null, opportunityId: null, createdAt: '2026-11-04' },
    { id: 'lead-3', name: 'Yuki Tanaka', company: '木曾户外株式会社', email: 'yuki@kiso.example', source: '转介绍', owner: '周衡', stage: 'proposal', accountId: 'acc-kiso', contactId: 'ctc-acc-kiso', opportunityId: 'opp-acc-kiso', createdAt: '2026-10-25' },
  ]
  db.crmActivities = [
    { id: 'act-1', subject: '确认春季补货数量', kind: '电话', at: '2026-11-12 10:00', accountId: 'acc-summit', owner: '周衡', status: 'planned' },
    { id: 'act-2', subject: '发送报价单', kind: '邮件', at: '2026-11-13 15:30', accountId: 'acc-ridge', owner: '林夏', status: 'planned' },
    { id: 'act-3', subject: '德国客户季度回顾', kind: '会议', at: '2026-11-08 09:00', accountId: 'acc-alpine', owner: '林夏', status: 'done' },
  ]
  db.crmReviews = [
    { id: 'review-1', source: 'Shopify', author: 'Emma R.', rating: 5, title: '轻便又结实', content: '帐篷搭建很快，适合周末露营。', sku: 'NW-TENT-2P-OLV', status: 'published' },
    { id: 'review-2', source: 'Amazon US', author: 'Daniel K.', rating: 3, title: '包装有改进空间', content: '产品不错，但外箱略有破损。', sku: 'NW-LAMP-OLV', status: 'pending' },
  ]
  db.crmTicketMessages = [
    { id: 'msg-tkt-1', ticketId: 'tkt-1', author: '客服 Nina', text: '已联系仓库核对装箱单。', at: '2026-11-08 12:00', internal: false },
    { id: 'msg-tkt-2', ticketId: 'tkt-1', author: '仓库', text: '确认少发一箱，安排补发。', at: '2026-11-08 15:30', internal: true },
  ]

  const owners = ['林夏', '周衡', '陈宁']
  const accountIds = db.crmAccounts.map(account => account.id)
  const stages = ['new', 'qualified', 'proposal', 'converted'] as const
  for (let index = 4; index <= 30; index++) {
    const accountId = accountIds[index % accountIds.length]
    const account = db.crmAccounts.find(item => item.id === accountId)

    db.crmLeads.push({
      id: `lead-${index}`,
      name: `${['Sofia', 'Lucas', 'Amelia', 'Noah', 'Mia'][index % 5]} ${index}`,
      company: account?.name ?? 'New Trail Buyer',
      email: `lead${index}@buyer.example`,
      source: ['展会', '网站表单', '转介绍', '广告'][index % 4],
      owner: owners[index % owners.length],
      stage: stages[index % stages.length],
      accountId: index % 4 === 0 ? accountId : null,
      contactId: index % 4 === 0 ? `ctc-${accountId}` : null,
      opportunityId: index % 4 === 0 ? `opp-${accountId}` : null,
      createdAt: `2026-${String(10 + (index % 3)).padStart(2, '0')}-${String((index % 25) + 1).padStart(2, '0')}`,
    })
  }
  for (let index = 1; index <= 17; index++) {
    const accountId = accountIds[index % accountIds.length]
    const account = db.crmAccounts.find(item => item.id === accountId)
    if (index > 7)
      db.crmContacts.push({ id: `ctc-extra-${index}`, accountId, name: ['Alex Morgan', '陈璐', 'Hiro Sato'][index % 3], title: index % 2 ? '采购经理' : '财务负责人', email: `contact${index}@buyer.example` })

    if (index > 8)
      db.crmOpportunities.push({ id: `opp-extra-${index}`, accountId, name: `${account?.name ?? '客户'} ${2027 + (index % 2)} 补货`, amount: minorFromDecimal(String(12000 + index * 1750)), currency: account?.currency ?? 'USD', stage: ['初步沟通', '需求确认', '报价', '谈判'][index % 4] })
  }
  for (let index = 4; index <= 40; index++)
    db.crmActivities.push({ id: `act-${index}`, subject: ['跟进报价', '确认库存', '安排回访', '发送合同'][index % 4], kind: ['电话', '邮件', '会议'][index % 3] as '电话' | '邮件' | '会议', at: `2026-${String(10 + (index % 3)).padStart(2, '0')}-${String((index % 25) + 1).padStart(2, '0')} ${String(9 + (index % 8)).padStart(2, '0')}:00`, accountId: accountIds[index % accountIds.length], owner: owners[index % owners.length], status: index % 4 === 0 ? 'done' : 'planned' })

  const orderRows = db.orders.slice(0, 20)
  for (let index = 2; index <= 20; index++) {
    const order = orderRows[index - 2]
    const accountId = accountIds[index % accountIds.length]
    const ticketId = `tkt-${index}`

    db.crmTickets.push({ id: ticketId, accountId, subject: ['少件补发', '退货进度', '尺寸咨询', '物流延迟'][index % 4], status: index % 3 === 0 ? 'resolved' : 'open', orderNo: order?.orderNo ?? null })
    db.crmTicketMessages.push({ id: `msg-${ticketId}-1`, ticketId, author: '客服 Nina', text: '已收到客户反馈，正在核对订单。', at: `2026-11-${String((index % 8) + 1).padStart(2, '0')} 10:00`, internal: false })
    db.crmTicketMessages.push({ id: `msg-${ticketId}-2`, ticketId, author: '运营团队', text: index % 3 === 0 ? '问题已解决并通知客户。' : '等待仓库提供处理结果。', at: `2026-11-${String((index % 8) + 1).padStart(2, '0')} 15:30`, internal: true })
  }
  for (let index = 3; index <= 30; index++)
    db.crmReviews.push({ id: `review-${index}`, source: ['Amazon US', 'Shopify', 'TikTok Shop'][index % 3], author: `Buyer ${index}`, rating: 1 + (index % 5), title: ['Great for camping', '包装需要改进', '轻便好用'][index % 3], content: '真实买家反馈样例，用于演示审核和回复流程。', sku: db.skus[index % db.skus.length].internalSku, status: index % 4 === 0 ? 'pending' : 'published' })
}

function addAdmin(db: MockDatabase) {
  db.adminIntegrations = [
    { id: 'int-amazon', name: 'Amazon SP-API', platform: 'Amazon', status: 'connected', account: 'Northwind US', lastSync: '2026-11-09 08:45' },
    { id: 'int-shopify', name: 'Shopify Admin', platform: 'Shopify', status: 'connected', account: 'northwind-outdoor.com', lastSync: '2026-11-09 08:30' },
    { id: 'int-tiktok', name: 'TikTok Shop', platform: 'TikTok Shop', status: 'needs_attention', account: 'Northwind TikTok US', lastSync: '2026-11-08 17:10' },
  ]
  db.adminModules = [
    { id: 'crm', name: 'CRM', description: '客户、线索、商机与售后工单', enabled: true },
    { id: 'finance', name: '财务', description: '结算、对账与利润', enabled: true },
    { id: 'agent', name: '智能体', description: '只读问答和待审批建议', enabled: true },
    { id: 'ads', name: '广告', description: '广告花费和分摊（后续模块）', enabled: false },
  ]
  db.adminDicts = [
    { id: 'dict-1', group: '工单状态', code: 'open', label: '处理中', active: true },
    { id: 'dict-2', group: '工单状态', code: 'resolved', label: '已解决', active: true },
    { id: 'dict-3', group: '线索来源', code: 'event', label: '展会', active: true },
  ]
  db.adminNotifications = [
    { id: 'notify-1', channel: '飞书机器人', event: '审批待办', enabled: true, target: '配置引用：vault:feishu-approval' },
    { id: 'notify-2', channel: '邮件', event: '导入失败', enabled: false, target: 'ops@example.invalid' },
  ]
  db.adminSettings = [
    { id: 'setting-1', key: 'single_user_mode', label: '单人模式', value: true, description: '演示环境允许提交人审批自己的建议。' },
    { id: 'setting-2', key: 'audit_strict', label: '严格审计', value: true, description: '所有写操作必须记录审计轨迹。' },
    { id: 'setting-3', key: 'default_currency', label: '默认币种', value: 'USD', description: '报表默认展示币种。' },
  ]
  db.accountTokens = [
    { id: 'tok-1', name: 'MCP 只读', prefix: 'csp_demo…', createdAt: '2026-10-15 09:00', lastUsedAt: '2026-11-08 18:20', revoked: false },
    { id: 'tok-2', name: '报表脚本（已撤销）', prefix: 'csp_old…', createdAt: '2026-08-02 11:30', lastUsedAt: '2026-10-01 07:45', revoked: true },
  ]
  db.accountSessions = [
    { id: 'session-current', device: 'Chrome · Windows', location: '上海', ip: '192.0.2.10', lastSeenAt: '2026-11-09 09:00', current: true },
    { id: 'session-mobile', device: 'Safari · iPhone', location: '杭州', ip: '192.0.2.21', lastSeenAt: '2026-11-08 18:20', current: false },
  ]
}

function addAgents(db: MockDatabase) {
  db.agentDefinitions = [
    { id: 'recon-explainer', name: '对账解释员', duty: '用只读工具解释异常，并起草待审批建议。不算钱，不写账。', model: 'placeholder-model-A', status: 'active', source: 'DeerFlow', tools: ['list_issues', 'get_recon_summary', 'propose_issue_note'], storeScope: '全部店铺', kind: 'deerflow' },
    { id: 'profit-analyst', name: '利润问答', duty: '按已算好的利润快照回答，并给出出处。', model: 'placeholder-model-A', status: 'active', source: 'DeerFlow', tools: ['get_profit', 'get_order'], storeScope: '全部店铺', kind: 'deerflow' },
    { id: 'crm-drafter', name: '客户跟进草稿', duty: '根据客户档案起草跟进。不改订单金额。', model: 'placeholder-model-B', status: 'paused', source: 'DeerFlow', tools: ['crm.get_account'], storeScope: 'CRM 客户', kind: 'deerflow' },
    { id: 'auditor-readonly', name: '审计只读', duty: '核对审计轨迹和运行记录。没有写工具。', model: 'placeholder-model-A', status: 'active', source: 'DeerFlow', tools: ['audit.list'], storeScope: '只读，全公司', kind: 'builtin_ask' },
  ]
  db.agentTools = [
    { name: 'get_profit', description: '读取利润快照', sideEffect: 'none', moduleCode: 'finance', active: true },
    { name: 'list_issues', description: '读取异常清单', sideEffect: 'none', moduleCode: 'finance', active: true },
    { name: 'get_order', description: '读取订单', sideEffect: 'none', moduleCode: 'orders', active: true },
    { name: 'propose_issue_note', description: '只创建待审批建议', sideEffect: 'propose', moduleCode: 'approvals', active: true },
  ]
  db.agentRuns = [
    { id: 'run-8841', agentName: '对账解释员', startedAt: '2026-11-09 01:12 UTC', durationMs: 4820, tokens: 2140, costUsd: 0.018, status: 'succeeded', question: '为什么 10 月结算对不平？' },
    { id: 'run-8836', agentName: '利润问答', startedAt: '2026-11-08 16:40 UTC', durationMs: 2310, tokens: 980, costUsd: 0.007, status: 'succeeded', question: '10 月帐篷利润是多少？' },
    { id: 'run-8820', agentName: '对账解释员', startedAt: '2026-11-08 09:05 UTC', durationMs: 9100, tokens: 3560, costUsd: 0.031, status: 'failed', question: '把差额直接改成平衡' },
    { id: 'run-8794', agentName: '审计只读', startedAt: '2026-11-07 22:18 UTC', durationMs: 1540, tokens: 640, costUsd: 0.004, status: 'succeeded', question: '最近的审计轨迹' },
  ]
  db.threads = [
    { id: 'th-1', title: '结算为什么不平', updatedAt: '2026-11-09 01:14', agentId: 'recon-explainer' },
    { id: 'th-2', title: '帐篷利润出处', updatedAt: '2026-11-08 16:42', agentId: 'profit-analyst' },
  ]
  db.messages = [
    { id: 'm1', threadId: 'th-1', role: 'user', text: '10 月结算为什么对不平？不要改数字。' },
    { id: 'm2', threadId: 'th-1', role: 'assistant', text: '我只读取系统已经记下的异常，没有重算金额。', toolName: 'list_issues', toolSummary: '只读：打开异常清单，金额沿用已存储差额。' },
  ]
  db.knowledgeBases = [
    { id: 'kb-rules', name: '对账规则', description: '原因码和费用映射说明', status: 'active' },
  ]
}

function addDraftStockDocs(db: MockDatabase) {
  const at = iso(10, 15, 4)
  const transferId = nextId(db, 'doc')

  db.stockDocs.push({
    id: transferId,
    docNo: 'TR-2026-001',
    docType: 'transfer',
    warehouseId: 'wh-cn-sz',
    toWarehouseId: 'wh-cn-nb',
    status: 'draft',
    remark: '草稿调拨，未过账，不改库存',
    createdBy: '林夏',
    createdAt: at,
  })
  db.stockDocLines.push({
    id: nextId(db, 'dln'),
    docId: transferId,
    internalSku: db.skus[0].internalSku,
    qtyExpected: 10,
    qtyActual: 0,
  })

  const countId = nextId(db, 'doc')

  db.stockDocs.push({
    id: countId,
    docNo: 'CT-2026-001',
    docType: 'count',
    warehouseId: 'wh-cn-sz',
    toWarehouseId: null,
    status: 'draft',
    remark: '草稿盘点，未过账，不改库存',
    createdBy: '林夏',
    createdAt: at,
  })
  db.stockDocLines.push({
    id: nextId(db, 'dln'),
    docId: countId,
    internalSku: db.skus[4].internalSku,
    qtyExpected: 20,
    qtyActual: 20,
  })
}

function addAlerts(db: MockDatabase) {
  const marker = actor('系统', 'admin', iso(11, 1, 1))

  const samples = [
    ['wh-fba-us', db.skus[1].internalSku, 8],
    ['wh-os-us', db.skus[2].internalSku, 0],
    ['wh-cn-sz', db.skus[3].internalSku, 12],
  ] as const

  for (const sample of samples) {
    const balance = db.balances.find(item => item.warehouseId === sample[0] && item.internalSku === sample[1])

    if (!balance)
      continue

    const delta = sample[2] - balance.onHand

    if (delta !== 0) {
      applyMovement(db, {
        warehouseId: sample[0],
        internalSku: sample[1],
        onHandDelta: delta,
        inTransitDelta: 0,
        reason: 'alert_sample',
        refType: 'seed',
        refId: 'alert-sample',
        actor: marker,
      })
    }
    db.alerts.push({
      id: nextId(db, 'alt'),
      warehouseId: sample[0],
      internalSku: sample[1],
      kind: sample[2] === 0 ? 'stockout' : 'low',
      threshold: 20,
      triggeredAt: marker.at,
      status: 'open',
    })
  }
}

export function buildSeed(): MockDatabase {
  const db = emptyDb()

  addMasters(db)
  addWarehouses(db)
  addListings(db)
  addSuppliers(db)
  addPurchases(db)
  addShipments(db)
  addOrders(db)
  addFinance(db)
  seedFinance(db)
  seedAds(db)
  addCrm(db)
  addAdmin(db)
  addAgents(db)
  addAgentModuleSeed(db)
  addDraftStockDocs(db)
  addAlerts(db)

  return db
}

export const MOCK_DB_VERSION = VERSION
