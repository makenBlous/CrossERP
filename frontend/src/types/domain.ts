/**
 * 旧五角色继续保留，16 个模板角色使用稳定 slug。模板角色通过权限表引擎
 * 映射到旧角色能力，确保现有 128 页的访问结果不变。
 */
export type Role =
  | 'admin' | 'operator' | 'finance' | 'viewer' | 'auditor'
  | 'owner_manager' | 'operations_manager' | 'store_operator' | 'advertising'
  | 'product_developer' | 'purchaser' | 'warehouse_logistics' | 'customer_service'
  | 'accountant' | 'finance_manager' | 'cashier' | 'hr_admin' | 'employee'
  | 'department_manager' | 'auditor_template' | 'external_viewer'

export type AppLocale = 'zh-CN' | 'en'

export type CurrencyCode = 'USD' | 'CNY' | 'EUR' | 'GBP' | 'JPY'

export interface Store {
  id: string
  name: string
  platform: 'Amazon' | 'Shopify' | 'TikTok Shop'
  marketplace: string
  currency: CurrencyCode
}

export interface DashboardKpi {
  sales: number
  fees: number
  netProfit: number
  grossMargin: number
  refundRate: number
  matchRate: number
  openIssues: number
  pendingApprovals: number
  currency: 'USD'
}

export interface TrendPoint {
  month: string
  sales: number
  profit: number
}

export interface StoreRank {
  storeId: string
  storeName: string
  platform: string
  marketplace: string
  sales: number
  profit: number
  matchRate: number
  currency: CurrencyCode
}

export interface ReasonSlice {
  code: string
  count: number
}

export interface DashboardPayload {
  periodLabel: string
  kpi: DashboardKpi
  trend: TrendPoint[]
  stores: StoreRank[]
  reasons: ReasonSlice[]
}

export interface OrderLine {
  sku: string
  title: string
  qty: number
  unitPrice: number
  currency: CurrencyCode
}

export interface OrderFee {
  type: string
  amount: number
  currency: CurrencyCode
}

export interface OrderEvent {
  time: string
  title: string
  detail: string
}

export interface OrderSummary {
  id: string
  orderNo: string
  storeId: string
  storeName: string
  platform: string
  marketplace: string
  orderedAt: string
  status: string
  statusCode?: string
  currency: CurrencyCode
  itemTotal: number
  feeTotal: number
  refund: number
  net: number
  fulfillment: string
}

export interface OrderDetail extends OrderSummary {
  buyerRef: string
  lines: OrderLine[]
  fees: OrderFee[]
  shipment: {
    warehouse: string
    carrier: string
    trackingNo: string
    shippedAt: string
  }
  timeline: OrderEvent[]
  related: Array<{ id: string; type: string; label: string; to?: string }>
}

export type StockAlert = 'ok' | 'low' | 'stockout'

export interface OnHandRow {
  sku: string
  name: string
  fbaQty: number
  fbaWarehouse: string
  overseasQty: number
  overseasWarehouse: string
  domesticQty: number
  domesticWarehouse: string
  dailySales: number
  coverDays: number
  alert: StockAlert
}

export interface InventoryTotals {
  fbaQty: number
  overseasQty: number
  domesticQty: number
  lowSku: number
  stockoutSku: number
}

export interface ProfitRow {
  sku: string
  name: string
  storeId: string
  storeName: string
  currency: CurrencyCode
  revenue: number
  platformFee: number
  ads: number
  firstMile: number
  cost: number
  profit: number
}

export interface StoreProfit {
  storeId: string
  storeName: string
  currency: CurrencyCode
  revenue: number
  platformFee: number
  ads: number
  firstMile: number
  cost: number
  profit: number
}

export interface ReconRun {
  id: string
  storeName: string
  period: string
  matched: number
  unmatched: number
  matchRate: number
  status: string
  finishedAt: string
}

export type IssueCode = 'DUPLICATE_ROW' | 'UNKNOWN_FEE_TYPE' | 'SETTLEMENT_UNBALANCED' | 'AMOUNT_MISMATCH'

export interface IssueRow {
  id: string
  code: IssueCode
  severity: 'high' | 'medium' | 'low'
  storeName: string
  refNo: string
  amount: number
  currency: CurrencyCode
  status: string
  summary: string
}

export type VoucherStatus = 'draft' | 'pending' | 'approved' | 'posted' | 'rejected'

export interface VoucherRow {
  id: string
  no: string
  period: string
  status: VoucherStatus
  debit: number
  credit: number
  currency: 'CNY'
  summary: string
  submitter: string
}

export type ApprovalStatus = 'pending' | 'approved' | 'rejected'

export interface ApprovalLine {
  account: string
  debit: number
  credit: number
}

export interface ApprovalItem {
  id: string
  title: string
  type: string
  submitter: string
  submittedAt: string
  amount: number
  currency: CurrencyCode
  status: ApprovalStatus
  summary: string
  lines: ApprovalLine[]
  comment?: string
  payloadHash?: string
  timeline?: Array<{ at: string; title: string; detail: string; actor?: string }>
}

export interface CrmAccount {
  id: string
  name: string
  type: string
  country: string
  owner: string
  currency: CurrencyCode
  pipeline: number
  orders: number
  status: string
  tags: string[]
}

export interface CrmContact {
  name: string
  title: string
  email: string
}

export interface CrmOpportunity {
  name: string
  amount: number
  currency: CurrencyCode
  stage: string
}

export interface CrmRelatedOrder {
  orderNo: string
  amount: number
  currency: CurrencyCode
  date: string
}

export interface CrmTicket {
  id: string
  subject: string
  status: string
}

export interface CrmAccountDetail extends CrmAccount {
  website: string
  email: string
  phone: string
  note: string
  contacts: CrmContact[]
  opportunities: CrmOpportunity[]
  relatedOrders: CrmRelatedOrder[]
  tickets: CrmTicket[]
}

export interface AgentDefinition {
  id: string
  name: string
  duty: string
  model: string
  status: 'active' | 'paused'
  source: 'DeerFlow'
  tools: string[]
  storeScope: string
}

export type AgentRunStatus = 'succeeded' | 'failed' | 'running'

export interface AgentRun {
  id: string
  agentName: string
  startedAt: string
  durationMs: number
  tokens: number
  costUsd: number
  status: AgentRunStatus
  question: string
}

export interface ChatThread {
  id: string
  title: string
  updatedAt: string
}

export interface ChatToolCall {
  name: string
  args: Record<string, string>
  summary: string
}

export interface ChatSuggestion {
  title: string
  detail: string
  amountLabel: string
  status: 'draft' | 'submitted'
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  toolCall?: ChatToolCall
  suggestion?: ChatSuggestion
}

export interface SkuListRow {
  id: string
  internalSku: string
  title: string
  brandName: string
  categoryName: string
  status: string
  listingCount: number
}

export interface SkuCostPoint {
  id: string
  validFrom: string
  validTo: string
  unitCost: number
  freight: number
  currency: CurrencyCode
}

export interface SkuDetailView {
  id: string
  internalSku: string
  title: string
  titleEn: string
  brandName: string
  brandId: string
  categoryName: string
  categoryId: string
  status: string
  costs: SkuCostPoint[]
  profits: Array<{ period: string; storeName: string; profit: number; currency: CurrencyCode }>
  orders: Array<{ id: string; orderNo: string; orderedAt: string; qty: number; status: string }>
  mappings: Array<{ id: string; storeName: string; platformSku: string; status: string }>
}

export interface CostListRow {
  id: string
  internalSku: string
  title: string
  validFrom: string
  validTo: string
  unitCost: number
  freight: number
  currency: CurrencyCode
}

export interface ListingListRow {
  id: string
  storeId: string
  storeName: string
  platform: string
  marketplace: string
  title: string
  platformListingId: string
  skuId: string
  internalSku: string
  status: string
  price: number
  currency: CurrencyCode
}

export interface CategoryRow {
  id: string
  name: string
  parentId: string
  parentName: string
  sortNo: number
  status: string
}

export interface BrandRow {
  id: string
  name: string
  skuCount: number
  status: string
}

export interface MappingRow {
  id: string
  storeId: string
  storeName: string
  platform: string
  platformSku: string
  internalSku: string
  status: string
}

export interface BundleRow {
  id: string
  parentInternalSku: string
  parentTitle: string
  childInternalSku: string
  childTitle: string
  qty: number
}

export interface ReturnRow {
  id: string
  orderId: string
  orderNo: string
  storeName: string
  amount: number
  currency: CurrencyCode
  postedAt: string
  status: string
}

export interface ExceptionRow {
  id: string
  code: string
  severity: string
  storeName: string
  refNo: string
  orderId: string
  amount: number
  currency: CurrencyCode
  status: string
  summary: string
}

export interface ChannelRow {
  id: string
  platform: string
  currency: CurrencyCode
  orders: number
  sales: number
  refunds: number
}

export interface FulfillmentRow {
  id: string
  orderNo: string
  storeName: string
  status: string
  fulfillment: string
  warehouse: string
  carrier: string
  trackingNo: string
  shippedAt: string
}

export interface TodoRow {
  id: string
  kind: string
  title: string
  detail: string
  at: string
  to: string
}

export interface CalendarEventRow {
  id: string
  title: string
  start: string
  kind: string
  to: string
}

export interface LookupOption {
  id: string
  label: string
}

export interface TimelineItem {
  id: string
  at: string
  title: string
  detail: string
  actor: string
}

export interface RelatedDoc {
  id: string
  type: string
  label: string
  to?: string
}

export interface WarehouseRow {
  id: string
  code: string
  name: string
  kind: string
  country: string
  status: string
}

export interface BalanceRow {
  id: string
  warehouseId: string
  warehouseName: string
  kind: string
  internalSku: string
  title: string
  onHand: number
  reserved: number
  inTransit: number
  unfulfillable: number
  available: number
}

export interface MovementRow {
  id: string
  occurredAt: string
  warehouseName: string
  internalSku: string
  qtyDelta: number
  inTransitDelta: number
  reason: string
  refType: string
  refId: string
  createdBy: string
}

export interface StockDocLineView {
  id: string
  internalSku: string
  qtyExpected: number
  qtyActual: number
  variance: number
  bookQty: number
}

export interface StockDocRow {
  id: string
  docNo: string
  docType: string
  warehouseId: string
  warehouseName: string
  toWarehouseId: string
  toWarehouseName: string
  status: string
  remark: string
  createdBy: string
  createdAt: string
  lineSummary: string
}

export interface StockDocDetail extends StockDocRow {
  lines: StockDocLineView[]
  timeline: TimelineItem[]
  related: RelatedDoc[]
}

export interface AlertRow {
  id: string
  warehouseId: string
  warehouseName: string
  internalSku: string
  kind: string
  threshold: number
  onHand: number
  triggeredAt: string
  status: string
}

export interface SupplierRow {
  id: string
  name: string
  country: string
  currency: CurrencyCode
  status: string
  contact: string
  openPo: number
}

export interface SupplierOrderView {
  id: string
  no: string
  status: string
  expectedAt: string
  amount: number
  currency: CurrencyCode
}

export interface SupplierDetailView {
  id: string
  name: string
  country: string
  currency: CurrencyCode
  status: string
  remark: string
  contacts: Array<{ id: string; name: string; email: string; phone: string }>
  orders: SupplierOrderView[]
  apBalance: number
  apCurrency: CurrencyCode
  timeline: TimelineItem[]
}

export interface PurchaseOrderRow {
  id: string
  no: string
  supplierId: string
  supplierName: string
  status: string
  currency: CurrencyCode
  expectedAt: string
  amount: number
  createdAt: string
}

export interface PurchaseLineView {
  id: string
  internalSku: string
  qty: number
  receivedQty: number
  unitCost: number
  currency: CurrencyCode
  amount: number
}

export interface PurchaseOrderDetailView extends PurchaseOrderRow {
  lines: PurchaseLineView[]
  receipts: Array<{ id: string; no: string; warehouseName: string; receivedAt: string; qty: number; status: string }>
  timeline: TimelineItem[]
  related: RelatedDoc[]
}

export interface ReceiptRow {
  id: string
  no: string
  purchaseOrderId: string
  purchaseOrderNo: string
  warehouseName: string
  receivedAt: string
  status: string
  qty: number
  orderedQty: number
  variance: number
}

export interface PurchaseReturnRow {
  id: string
  no: string
  supplierId: string
  supplierName: string
  purchaseOrderId: string
  purchaseOrderNo: string
  status: string
  currency: CurrencyCode
  amount: number
}

export interface StatementRow {
  id: string
  no: string
  supplierId: string
  supplierName: string
  period: string
  status: string
  currency: CurrencyCode
  amount: number
  receivedAmount: number
  paidAmount: number
  variance: number
}

export interface ShipmentRow {
  id: string
  no: string
  carrierId: string
  carrierName: string
  fromName: string
  toName: string
  status: string
  departedAt: string
  arrivedAt: string
  skuSummary: string
  containerNo: string
}

export interface ShipmentDetailView extends ShipmentRow {
  warehouseFrom: string
  warehouseTo: string
  volumetricKg: string
  lines: Array<{ id: string; internalSku: string; qty: number }>
  charges: Array<{ id: string; chargeType: string; amount: number; currency: CurrencyCode }>
  tracking: Array<{ id: string; occurredAt: string; description: string }>
  timeline: TimelineItem[]
  related: RelatedDoc[]
}

export interface CarrierRow {
  id: string
  name: string
  status: string
  rateCount: number
}

export interface RateCardRow {
  id: string
  carrierId: string
  carrierName: string
  dest: string
  unit: string
  price: number
  currency: CurrencyCode
  validFrom: string
  validTo: string
}

export interface TrackingRow {
  id: string
  shipmentId: string
  shipmentNo: string
  occurredAt: string
  description: string
  status: string
}

export interface FreightCheckRow {
  id: string
  shipmentId: string
  shipmentNo: string
  billAmount: number
  estimateAmount: number
  currency: CurrencyCode
  variance: number
  status: string
}

export interface SupplyLookups {
  skus: LookupOption[]
  suppliers: LookupOption[]
  warehouses: LookupOption[]
  carriers: LookupOption[]
  purchaseOrders: LookupOption[]
}
