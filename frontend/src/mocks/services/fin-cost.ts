import type { Actor } from '@/types/entities'
import type { CurrencyCode } from '@/types/domain'
import { FlowError } from '@/mocks/services/errors'
import { writeAudit } from '@/mocks/services/audit'
import { fieldAccess, roleSubject } from '@/utils/permission-engine'

export type FinCostStatus = 'draft' | 'pending' | 'posted' | 'rejected'

export interface LedgerRow {
  id: string
  occurredAt: string
  warehouseName: string
  internalSku: string
  batch: string
  qtyDelta: number
  amountDelta?: number
  balanceQty: number
  balanceAmount?: number
  valuationMethod: 'moving_average'
  refId: string
  actorId: string
}

export interface LandedCostAllocation {
  id: string
  internalSku: string
  batch: string
  warehouseName: string
  chargeableWeight: number
  amount: number
  toStock: number
  toCogs: number
  tailFlag: boolean
}

export interface LandedCostVoucher {
  id: string
  no: string
  shipmentId: string
  period: string
  status: FinCostStatus
  docstatus: 0 | 1 | 2
  basis: 'chargeable_weight'
  poolAmount: number
  currency: CurrencyCode
  submitterId: string
  submitterName: string
  approvedById?: string
  approvedByName?: string
  allocations: LandedCostAllocation[]
  timeline: Array<{ id: string; at: string; title: string; detail: string; actorId: string; actor: string }>
}

export interface GrniRow {
  id: string
  receiptNo: string
  supplier: string
  receivedAt: string
  estimatedAmount: number
  invoicedAmount: number
  balanceAmount: number
  offsetProgress: number
  status: 'open' | 'partial' | 'cleared'
  nextAction: string
}

interface FinCostState {
  ledger: LedgerRow[]
  vouchers: LandedCostVoucher[]
  grni: GrniRow[]
}

const STORAGE_KEY = 'crosserp-fin-cost-v1'

const seedState: FinCostState = {
  ledger: [
    { id: 'led-001', occurredAt: '2026-11-01T08:00:00+08:00', warehouseName: 'FBA US', internalSku: 'SKU-A', batch: 'BATCH-A-01', qtyDelta: 10, amountDelta: 7200000, balanceQty: 10, balanceAmount: 7200000, valuationMethod: 'moving_average', refId: 'GRN-2026-001', actorId: 'demo-warehouse-logistics' },
    { id: 'led-002', occurredAt: '2026-11-03T10:00:00+08:00', warehouseName: 'FBA US', internalSku: 'SKU-A', batch: 'BATCH-A-01', qtyDelta: -4, amountDelta: -2880000, balanceQty: 6, balanceAmount: 4320000, valuationMethod: 'moving_average', refId: 'SO-2026-001', actorId: 'demo-store-operator' },
    { id: 'led-003', occurredAt: '2026-11-04T14:30:00+08:00', warehouseName: 'FBA US', internalSku: 'SKU-B', batch: 'BATCH-B-01', qtyDelta: 12, amountDelta: 6000000, balanceQty: 12, balanceAmount: 6000000, valuationMethod: 'moving_average', refId: 'GRN-2026-002', actorId: 'demo-warehouse-logistics' },
    { id: 'led-004', occurredAt: '2026-11-05T09:20:00+08:00', warehouseName: 'FBA US', internalSku: 'SKU-B', batch: 'BATCH-B-01', qtyDelta: -4, amountDelta: -2000000, balanceQty: 8, balanceAmount: 4000000, valuationMethod: 'moving_average', refId: 'SO-2026-002', actorId: 'demo-store-operator' },
  ],
  vouchers: [
    {
      id: 'lcv-2026-001',
      no: 'LCV-2026-001',
      shipmentId: 'shp-001',
      period: '2026-11',
      status: 'pending',
      docstatus: 0,
      basis: 'chargeable_weight',
      poolAmount: 1200001,
      currency: 'CNY',
      submitterId: 'demo-warehouse-logistics',
      submitterName: '演示仓储/物流',
      allocations: [
        { id: 'alloc-1', internalSku: 'SKU-A', batch: 'BATCH-A-01', warehouseName: 'FBA US', chargeableWeight: 20000, amount: 600001, toStock: 360001, toCogs: 240000, tailFlag: false },
        { id: 'alloc-2', internalSku: 'SKU-B', batch: 'BATCH-B-01', warehouseName: 'FBA US', chargeableWeight: 20000, amount: 600000, toStock: 400000, toCogs: 200000, tailFlag: true },
      ],
      timeline: [
        { id: 'tl-1', at: '2026-11-06T10:00:00+08:00', title: '创建分摊单', detail: '按计费重生成演示分摊预览。', actorId: 'demo-warehouse-logistics', actor: '演示仓储/物流' },
        { id: 'tl-2', at: '2026-11-06T10:05:00+08:00', title: '提交审批', detail: '金额由确定性分摊规则计算，等待财务主管审批。', actorId: 'demo-warehouse-logistics', actor: '演示仓储/物流' },
      ],
    },
    {
      id: 'lcv-2026-002',
      no: 'LCV-2026-002',
      shipmentId: 'shp-002',
      period: '2026-10',
      status: 'posted',
      docstatus: 1,
      basis: 'chargeable_weight',
      poolAmount: 850000,
      currency: 'CNY',
      submitterId: 'demo-accountant',
      submitterName: '演示会计',
      approvedById: 'demo-finance-manager',
      approvedByName: '演示财务主管',
      allocations: [{ id: 'alloc-3', internalSku: 'SKU-A', batch: 'BATCH-A-00', warehouseName: '海外仓 US', chargeableWeight: 18000, amount: 850000, toStock: 850000, toCogs: 0, tailFlag: false }],
      timeline: [
        { id: 'tl-3', at: '2026-10-28T09:00:00+08:00', title: '已过账', detail: '审批通过，已写入库存成本。', actorId: 'demo-finance-manager', actor: '演示财务主管' },
      ],
    },
    {
      id: 'lcv-2026-003',
      no: 'LCV-2026-003',
      shipmentId: 'shp-003',
      period: '2026-11',
      status: 'draft',
      docstatus: 0,
      basis: 'chargeable_weight',
      poolAmount: 1200001,
      currency: 'CNY',
      submitterId: 'demo-accountant',
      submitterName: '演示会计',
      allocations: [
        { id: 'alloc-4', internalSku: 'SKU-A', batch: 'BATCH-A-02', warehouseName: 'FBA US', chargeableWeight: 20000, amount: 600001, toStock: 600001, toCogs: 0, tailFlag: false },
        { id: 'alloc-5', internalSku: 'SKU-B', batch: 'BATCH-B-02', warehouseName: 'FBA US', chargeableWeight: 20000, amount: 600000, toStock: 600000, toCogs: 0, tailFlag: true },
      ],
      timeline: [{ id: 'tl-4', at: '2026-11-08T11:00:00+08:00', title: '创建草稿', detail: '金额待提交审批，仍由确定性分摊规则生成。', actorId: 'demo-accountant', actor: '演示会计' }],
    },
    {
      id: 'lcv-2026-004',
      no: 'LCV-2026-004',
      shipmentId: 'shp-004',
      period: '2026-11',
      status: 'pending',
      docstatus: 0,
      basis: 'chargeable_weight',
      poolAmount: 320000,
      currency: 'CNY',
      submitterId: 'demo-finance-manager',
      submitterName: '演示财务主管',
      allocations: [{ id: 'alloc-6', internalSku: 'SKU-A', batch: 'BATCH-A-03', warehouseName: 'FBA US', chargeableWeight: 12000, amount: 320000, toStock: 320000, toCogs: 0, tailFlag: false }],
      timeline: [{ id: 'tl-5', at: '2026-11-09T11:00:00+08:00', title: '待审批', detail: '演示自审拒绝：制单人与审批人不能相同。', actorId: 'demo-finance-manager', actor: '演示财务主管' }],
    },
  ],
  grni: [
    { id: 'grni-001', receiptNo: 'GRN-2026-001', supplier: '宁波远途供应链', receivedAt: '2026-11-01', estimatedAmount: 7200000, invoicedAmount: 7000000, balanceAmount: 200000, offsetProgress: 97, status: 'partial', nextAction: '财务主管确认差额留到下期' },
    { id: 'grni-002', receiptNo: 'GRN-2026-002', supplier: '东莞山野用品', receivedAt: '2026-11-04', estimatedAmount: 6000000, invoicedAmount: 6000000, balanceAmount: 0, offsetProgress: 100, status: 'cleared', nextAction: '已完成票到冲暂估' },
    { id: 'grni-003', receiptNo: 'GRN-2026-003', supplier: '义乌轻量户外', receivedAt: '2026-11-08', estimatedAmount: 4800000, invoicedAmount: 0, balanceAmount: 4800000, offsetProgress: 0, status: 'open', nextAction: '等待采购发票到达' },
  ],
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function loadState(): FinCostState {
  if (typeof localStorage === 'undefined')
    return clone(seedState)

  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw)
      return { ...clone(seedState), ...JSON.parse(raw) as Partial<FinCostState> }
  }
  catch {
    // 损坏的演示缓存回退到固定样本。
  }

  return clone(seedState)
}

const state = loadState()

function persist() {
  if (typeof localStorage !== 'undefined')
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

export function listLedger(actor?: Actor) {
  const rows = clone(state.ledger)
  const canSeeCost = !actor || fieldAccess(roleSubject(actor.role, actor.userId), 'cost') !== 'hidden'

  if (canSeeCost)
    return rows

  return rows.map(row => {
    const masked = { ...row }

    delete masked.amountDelta
    delete masked.balanceAmount

    return masked
  })
}

export function listLandedCosts() {
  return clone(state.vouchers)
}

export function getLandedCost(id: string) {
  const voucher = state.vouchers.find(item => item.id === id)

  return voucher ? clone(voucher) : null
}

function appendTimeline(voucher: LandedCostVoucher, actor: Actor, title: string, detail: string) {
  voucher.timeline.push({ id: `${voucher.id}-${voucher.timeline.length + 1}`, at: actor.at, title, detail, actorId: actor.userId, actor: actor.name })
}

export function submitLandedCost(id: string, actor: Actor) {
  const voucher = state.vouchers.find(item => item.id === id)
  if (!voucher)
    throw new FlowError('找不到到岸成本分摊单')
  if (voucher.status !== 'draft' && voucher.status !== 'rejected')
    throw new FlowError('只有草稿或已驳回的分摊单可以提交')
  if (voucher.submitterId !== actor.userId)
    voucher.submitterId = actor.userId
  voucher.submitterName = actor.name
  voucher.status = 'pending'
  appendTimeline(voucher, actor, '提交审批', '提交后由另一位财务主管审批，批准前不会写入台账。')
  persist()

  return clone(voucher)
}

export function approveLandedCost(id: string, actor: Actor) {
  const voucher = state.vouchers.find(item => item.id === id)
  if (!voucher)
    throw new FlowError('找不到到岸成本分摊单')
  if (voucher.status !== 'pending')
    throw new FlowError('只有待审批的分摊单可以审批')
  if (voucher.submitterId === actor.userId)
    throw new FlowError('职责分离：制单人不能审批自己的分摊单')

  voucher.status = 'posted'
  voucher.docstatus = 1
  voucher.approvedById = actor.userId
  voucher.approvedByName = actor.name
  for (const allocation of voucher.allocations) {
    if (!allocation.toStock)
      continue

    const current = state.ledger.find(item => item.warehouseName === allocation.warehouseName && item.internalSku === allocation.internalSku && item.batch === allocation.batch)
    if (!current) {
      state.ledger.push({
        id: `${voucher.id}-${allocation.id}`,
        occurredAt: actor.at,
        warehouseName: allocation.warehouseName,
        internalSku: allocation.internalSku,
        batch: allocation.batch,
        qtyDelta: 0,
        amountDelta: allocation.toStock,
        balanceQty: 0,
        balanceAmount: allocation.toStock,
        valuationMethod: 'moving_average',
        refId: voucher.no,
        actorId: actor.userId,
      })
      continue
    }

    current.balanceAmount = (current.balanceAmount ?? 0) + allocation.toStock
    state.ledger.push({
      ...current,
      id: `${voucher.id}-${allocation.id}`,
      occurredAt: actor.at,
      qtyDelta: 0,
      amountDelta: allocation.toStock,
      balanceAmount: current.balanceAmount,
      refId: voucher.no,
      actorId: actor.userId,
    })
  }
  appendTimeline(voucher, actor, '批准并过账', '审批通过，分摊金额写入库存与销售成本。')
  persist()

  return clone(voucher)
}

export function listGrni() {
  return clone(state.grni)
}

export function appendAudit(actor: Actor, action: string, refType: string, refId: string, summary: string, db: Parameters<typeof writeAudit>[0]) {
  writeAudit(db, actor, action, refType, refId, summary)
}
