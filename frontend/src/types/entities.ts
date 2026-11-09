import type { CurrencyCode, IssueCode, Role } from '@/types/domain'
import type { Minor } from '@/utils/money'

export type Platform = 'Amazon' | 'Shopify' | 'TikTok Shop'
export type WarehouseKind = 'fba' | 'overseas' | 'domestic'
export type DocType = 'inbound' | 'outbound' | 'transfer' | 'count'

export interface Actor {
  name: string
  role: Role
  at: string
}

export interface Company {
  id: string
  name: string
  currency: CurrencyCode
}

export interface Shop {
  id: string
  companyId: string
  name: string
  platform: Platform
  marketplace: string
  country: string
  currency: CurrencyCode
}

export interface Brand {
  id: string
  name: string
  active: boolean
}

export interface Category {
  id: string
  parentId: string | null
  name: string
  sortNo: number
  active: boolean
}

export interface Sku {
  id: string
  internalSku: string
  title: string
  titleEn: string
  brandId: string
  categoryId: string
  active: boolean
}

export interface Listing {
  id: string
  storeId: string
  skuId: string
  platformListingId: string
  title: string
  status: string
  price: Minor
  currency: CurrencyCode
}

export interface SkuMapping {
  id: string
  storeId: string
  platformSku: string
  internalSku: string
  status: 'confirmed' | 'suggested'
}

export interface Bundle {
  id: string
  parentInternalSku: string
  childInternalSku: string
  qty: number
}

export interface SkuCost {
  id: string
  internalSku: string
  validFrom: string
  validTo: string | null
  unitCost: Minor
  currency: CurrencyCode
  freightPerUnit: Minor
}

export interface FxRate {
  id: string
  period: string
  fromCcy: CurrencyCode
  toCcy: CurrencyCode
  rate: string
  source: string
}

export interface SalesOrder {
  id: string
  storeId: string
  orderNo: string
  orderedAt: string
  buyerRef: string
  status: string
  currency: CurrencyCode
  fulfillment: 'FBA' | 'FBM' | 'Merchant'
  warehouseId: string
  carrierName: string
  trackingNo: string
  shippedAt: string | null
  refund: Minor
}

export interface SalesOrderLine {
  id: string
  orderId: string
  internalSku: string
  title: string
  qty: number
  unitPrice: Minor
  currency: CurrencyCode
}

export interface SalesReturn {
  id: string
  storeId: string
  orderId: string
  amount: Minor
  currency: CurrencyCode
  postedAt: string
  status: string
}

export interface Warehouse {
  id: string
  code: string
  name: string
  kind: WarehouseKind
  country: string
  storeId: string | null
  active: boolean
}

export interface StockBalance {
  id: string
  warehouseId: string
  internalSku: string
  onHand: number
  reserved: number
  inTransit: number
  unfulfillable: number
}

export interface StockMovement {
  id: string
  warehouseId: string
  internalSku: string
  qtyDelta: number
  inTransitDelta: number
  reason: string
  refType: string
  refId: string
  occurredAt: string
  createdBy: string
}

export interface StockDoc {
  id: string
  docNo: string
  docType: DocType
  warehouseId: string
  toWarehouseId: string | null
  status: string
  remark: string
  createdBy: string
  createdAt: string
}

export interface StockDocLine {
  id: string
  docId: string
  internalSku: string
  qtyExpected: number
  qtyActual: number
}

export interface StockAlert {
  id: string
  warehouseId: string
  internalSku: string
  kind: 'low' | 'stockout'
  threshold: number
  triggeredAt: string
  status: string
}

export interface Supplier {
  id: string
  name: string
  country: string
  currency: CurrencyCode
  status: string
  remark: string
}

export interface SupplierContact {
  id: string
  supplierId: string
  name: string
  email: string
  phone: string
}

export interface PurchaseOrder {
  id: string
  no: string
  supplierId: string
  status: string
  currency: CurrencyCode
  expectedAt: string
  createdBy: string
  createdAt: string
}

export interface PurchaseOrderLine {
  id: string
  purchaseOrderId: string
  internalSku: string
  qty: number
  receivedQty: number
  unitCost: Minor
  currency: CurrencyCode
}

export interface PurchaseReceipt {
  id: string
  no: string
  purchaseOrderId: string
  warehouseId: string
  receivedAt: string
  status: string
}

export interface PurchaseReceiptLine {
  id: string
  receiptId: string
  purchaseOrderLineId: string
  qty: number
}

export interface PurchaseReturn {
  id: string
  no: string
  supplierId: string
  purchaseOrderId: string
  status: string
  currency: CurrencyCode
  amount: Minor
}

export interface SupplierStatement {
  id: string
  no: string
  supplierId: string
  period: string
  status: string
  currency: CurrencyCode
  amount: Minor
}

export interface Carrier {
  id: string
  name: string
  active: boolean
}

export interface ShippingRate {
  id: string
  carrierId: string
  dest: string
  unit: string
  price: Minor
  currency: CurrencyCode
  validFrom: string
  validTo: string | null
}

export interface Shipment {
  id: string
  no: string
  carrierId: string
  warehouseFrom: string
  warehouseTo: string
  status: string
  departedAt: string | null
  arrivedAt: string | null
}

export interface ShipmentLine {
  id: string
  shipmentId: string
  internalSku: string
  qty: number
}

export interface ShipmentCharge {
  id: string
  shipmentId: string
  chargeType: string
  amount: Minor
  currency: CurrencyCode
}

export interface TrackingEvent {
  id: string
  shipmentId: string
  occurredAt: string
  description: string
}

export interface FreightCheck {
  id: string
  shipmentId: string
  billAmount: Minor
  estimateAmount: Minor
  currency: CurrencyCode
  variance: Minor
  status: string
}

export interface Settlement {
  id: string
  storeId: string
  platform: Platform
  externalId: string
  periodStart: string
  periodEnd: string
  total: Minor
  currency: CurrencyCode
  status: string
}

export interface ReconRunEntity {
  id: string
  storeId: string
  period: string
  matched: number
  unmatched: number
  status: string
  finishedAt: string
}

export interface IssueEntity {
  id: string
  code: IssueCode
  severity: 'high' | 'medium' | 'low'
  storeId: string
  refNo: string
  amount: Minor
  currency: CurrencyCode
  status: string
  summary: string
}

export interface VoucherEntity {
  id: string
  no: string
  period: string
  status: 'draft' | 'pending' | 'posted'
  debit: Minor
  credit: Minor
  currency: 'CNY'
  summary: string
  submitter: string
}

export interface ProfitSnapshot {
  id: string
  period: string
  internalSku: string
  storeId: string
  revenue: Minor
  fees: Minor
  refunds: Minor
  cogs: Minor
  freight: Minor
  ads: Minor
  profit: Minor
  currency: CurrencyCode
  calcVersion: string
}

export interface ApprovalEntity {
  id: string
  targetType: string
  targetId: string
  title: string
  type: string
  submitter: string
  submittedAt: string
  amount: Minor
  currency: CurrencyCode
  status: 'pending' | 'approved' | 'rejected'
  summary: string
  storeId: string | null
  lines: Array<{ account: string; debit: Minor; credit: Minor }>
}

export interface CrmAccountEntity {
  id: string
  name: string
  kind: string
  country: string
  owner: string
  currency: CurrencyCode
  status: string
  tags: string[]
  website: string
  email: string
  phone: string
  note: string
}

export interface CrmContactEntity {
  id: string
  accountId: string
  name: string
  title: string
  email: string
}

export interface CrmOpportunityEntity {
  id: string
  accountId: string
  name: string
  amount: Minor
  currency: CurrencyCode
  stage: string
}

export interface CrmTicketEntity {
  id: string
  accountId: string
  subject: string
  status: string
  orderNo: string | null
}

export interface AgentDefinitionEntity {
  id: string
  name: string
  duty: string
  model: string
  status: 'active' | 'paused'
  source: 'DeerFlow'
  tools: string[]
  storeScope: string
  kind: 'builtin_ask' | 'deerflow'
}

export interface AgentTool {
  name: string
  description: string
  sideEffect: 'none' | 'propose'
  moduleCode: string
  active: boolean
}

export interface AgentRunEntity {
  id: string
  agentName: string
  startedAt: string
  durationMs: number
  tokens: number
  costUsd: number
  status: 'succeeded' | 'failed' | 'running'
  question: string
}

export interface ThreadEntity {
  id: string
  title: string
  updatedAt: string
  agentId: string
}

export interface MessageEntity {
  id: string
  threadId: string
  role: 'user' | 'assistant'
  text: string
  toolName?: string
  toolSummary?: string
}

export interface AuditEvent {
  id: string
  at: string
  actor: string
  actorRole: Role
  action: string
  refType: string
  refId: string
  summary: string
}

export interface AccountEntity {
  code: string
  name: string
  direction: 'debit' | 'credit'
  active: boolean
}

export interface AdsCampaign {
  id: string
  storeId: string
  name: string
  status: string
  spend: Minor
  currency: CurrencyCode
}

export interface ArInvoice {
  id: string
  storeId: string
  amount: Minor
  currency: CurrencyCode
  status: string
  dueAt: string
}

export interface ApInvoice {
  id: string
  supplierId: string
  amount: Minor
  currency: CurrencyCode
  status: string
  dueAt: string
}

export interface KnowledgeBase {
  id: string
  name: string
  description: string
  status: string
}

export interface DeerflowConnection {
  id: string
  baseUrl: string
  enabled: boolean
  lastOkAt: string | null
  lastError: string
  configRef: string
}

export interface MockMeta {
  version: number
  seed: number
  seq: number
  generatedAt: string
}

export interface MockDatabase {
  meta: MockMeta
  company: Company
  stores: Shop[]
  brands: Brand[]
  categories: Category[]
  skus: Sku[]
  listings: Listing[]
  mappings: SkuMapping[]
  bundles: Bundle[]
  skuCosts: SkuCost[]
  fxRates: FxRate[]
  orders: SalesOrder[]
  orderLines: SalesOrderLine[]
  returns: SalesReturn[]
  warehouses: Warehouse[]
  balances: StockBalance[]
  movements: StockMovement[]
  stockDocs: StockDoc[]
  stockDocLines: StockDocLine[]
  alerts: StockAlert[]
  suppliers: Supplier[]
  supplierContacts: SupplierContact[]
  purchaseOrders: PurchaseOrder[]
  purchaseOrderLines: PurchaseOrderLine[]
  receipts: PurchaseReceipt[]
  receiptLines: PurchaseReceiptLine[]
  purchaseReturns: PurchaseReturn[]
  statements: SupplierStatement[]
  carriers: Carrier[]
  rateCards: ShippingRate[]
  shipments: Shipment[]
  shipmentLines: ShipmentLine[]
  shipmentCharges: ShipmentCharge[]
  tracking: TrackingEvent[]
  freightChecks: FreightCheck[]
  settlements: Settlement[]
  reconRuns: ReconRunEntity[]
  issues: IssueEntity[]
  vouchers: VoucherEntity[]
  profitSnapshots: ProfitSnapshot[]
  approvals: ApprovalEntity[]
  crmAccounts: CrmAccountEntity[]
  crmContacts: CrmContactEntity[]
  crmOpportunities: CrmOpportunityEntity[]
  crmTickets: CrmTicketEntity[]
  agentDefinitions: AgentDefinitionEntity[]
  agentTools: AgentTool[]
  agentRuns: AgentRunEntity[]
  threads: ThreadEntity[]
  messages: MessageEntity[]
  audit: AuditEvent[]
  accounts: AccountEntity[]
  adsCampaigns: AdsCampaign[]
  arInvoices: ArInvoice[]
  apInvoices: ApInvoice[]
  knowledgeBases: KnowledgeBase[]
  deerflow: DeerflowConnection
}
