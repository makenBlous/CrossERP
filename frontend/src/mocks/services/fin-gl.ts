import type { Actor, MockDatabase, VoucherEntity } from '@/types/entities'
import { writeAudit } from '@/mocks/services/audit'
import { nextId } from '@/mocks/services/ids'
import { requireActorPermission } from '@/utils/service-permissions'
import { minorFromDecimal } from '@/utils/money'

export interface GlReconcileRow {
  id: string
  period: string
  warehouse: string
  sku: string
  ledgerBalance: number
  inventoryAccount: number
  inventoryTransit: number
  difference: number
  status: 'matched' | 'difference'
}

export interface OpeningBatch {
  id: string
  status: 'collecting' | 'trial_balanced' | 'pending_approval' | 'live'
  trialDebit: number
  trialCredit: number
  inventoryLedger: number
  inventoryAccount: number
  stockRows: Array<{ sku: string; warehouse: string; qty: number; amount: number }>
  invoiceRows: Array<{ side: 'ar' | 'ap'; partner: string; docNo: string; amount: number }>
  preparedBy?: string
  activatedBy?: string
  approvedBy?: string
}

interface ReopenRequest {
  id: string
  period: string
  reason: string
  impact: string
  requestedBy: string
  requestedByName: string
  approvedBy?: string
  approvedByName?: string
  status: 'pending' | 'rejected' | 'approved'
  cooldownUntil: string
}

interface FinGlState {
  opening: OpeningBatch
  reopenRequests: ReopenRequest[]
}

const STORAGE_KEY = 'crosserp-fin-gl-v1'

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T

function initialState(): FinGlState {
  return {
    opening: {
      id: 'opening-2026-10-demo',
      status: 'collecting',
      trialDebit: minorFromDecimal('1500'),
      trialCredit: minorFromDecimal('1499.9000'),
      inventoryLedger: minorFromDecimal('800'),
      inventoryAccount: minorFromDecimal('800'),
      stockRows: [{ sku: 'SKU-A', warehouse: 'FBA-US', qty: 10, amount: minorFromDecimal('800') }],
      invoiceRows: [{ side: 'ar', partner: 'Amazon US', docNo: 'AR-OPEN-001', amount: minorFromDecimal('200') }, { side: 'ap', partner: '演示供应商', docNo: 'AP-OPEN-001', amount: minorFromDecimal('300') }],
    },
    reopenRequests: [],
  }
}

let state: FinGlState | undefined

function loadState() {
  if (state)
    return state

  if (typeof localStorage === 'undefined') {
    state = initialState()

    return state
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY)

    state = raw ? JSON.parse(raw) as FinGlState : initialState()
  }
  catch {
    state = initialState()
  }

  return state
}

function persist() {
  if (typeof localStorage !== 'undefined')
    localStorage.setItem(STORAGE_KEY, JSON.stringify(loadState()))
}

export function listGlReconcile() {
  return clone<GlReconcileRow[]>([
    { id: 'glr-9175001', period: '2026-10', warehouse: 'FBA-US', sku: 'SKU-A', ledgerBalance: minorFromDecimal('917.5001'), inventoryAccount: minorFromDecimal('800'), inventoryTransit: minorFromDecimal('117.5001'), difference: 0, status: 'matched' },
    { id: 'glr-diff-01', period: '2026-10', warehouse: '海外仓-US', sku: 'SKU-B', ledgerBalance: minorFromDecimal('120.0000'), inventoryAccount: minorFromDecimal('118.0000'), inventoryTransit: 0, difference: minorFromDecimal('2'), status: 'difference' },
  ])
}

export function getOpening() {
  return clone(loadState().opening)
}

export function balanceOpening(db: MockDatabase, actor: Actor) {
  requireActorPermission(actor, 'journal_entry:create')

  const opening = loadState().opening

  opening.trialCredit = opening.trialDebit
  opening.status = 'trial_balanced'
  opening.preparedBy = actor.userId
  writeAudit(db, actor, 'opening_trial_balanced', 'opening_batch', opening.id, '期初试算已补齐，借贷合计相等。')
  persist()

  return clone(opening)
}

export function activateOpening(db: MockDatabase, actor: Actor) {
  requireActorPermission(actor, 'journal_entry:submit')

  const opening = loadState().opening
  if (opening.trialDebit !== opening.trialCredit)
    throw new Error('试算不平，不能启用期初')
  if (opening.inventoryLedger !== opening.inventoryAccount)
    throw new Error('库存数量金额与库存科目不齐，不能启用期初')
  if (opening.status === 'live')
    throw new Error('期初已启用，不能重复启用')
  if (opening.preparedBy && opening.preparedBy === actor.userId)
    throw new Error('启用需要另一人批准，制单人不能自批')

  opening.status = 'live'
  opening.approvedBy = actor.userId
  writeAudit(db, actor, 'opening_activated', 'opening_batch', opening.id, '期初启用完成，业务单据现在可以过账。')
  persist()

  return clone(opening)
}

export function listReopenRequests() {
  return clone(loadState().reopenRequests)
}

export function createReopenRequest(db: MockDatabase, actor: Actor, period: string, reason: string, impact: string) {
  requireActorPermission(actor, 'period_closing_voucher:cancel')
  if (!reason.trim() || !impact.trim())
    throw new Error('反结账必须填写原因和影响范围')

  const existing = loadState().reopenRequests.find(row => row.period === period && row.status === 'pending')
  if (existing)
    throw new Error('该期间已有待审批的反结账申请')

  const row: ReopenRequest = { id: `reopen-${Date.now()}`, period, reason: reason.trim(), impact: impact.trim(), requestedBy: actor.userId, requestedByName: actor.name, status: 'pending', cooldownUntil: new Date(Date.now() + 86400000).toISOString() }

  loadState().reopenRequests.unshift(row)
  writeAudit(db, actor, 'period_reopen_requested', 'period_reopen_request', row.id, `申请反结账 ${period}：${row.reason}；影响范围：${row.impact}。`)
  persist()

  return clone(row)
}

export function approveReopen(db: MockDatabase, actor: Actor, requestId: string) {
  requireActorPermission(actor, 'period_closing_voucher:cancel')

  const request = loadState().reopenRequests.find(row => row.id === requestId)
  if (!request)
    throw new Error('反结账申请不存在')
  if (request.status !== 'pending')
    throw new Error('反结账申请已处理')
  if (request.requestedBy === actor.userId)
    throw new Error('申请人不能批准自己的反结账申请')
  if (actor.userId === 'demo-finance')
    throw new Error('原结账人不能批准反结账申请')
  if (Date.parse(request.cooldownUntil) > Date.now())
    throw new Error('敏感操作冷静期未结束，需满一个自然日后批准')

  request.status = 'approved'
  request.approvedBy = actor.userId
  request.approvedByName = actor.name
  writeAudit(db, actor, 'period_reopened', 'period_reopen_request', request.id, `反结账批准，期间 ${request.period} 回到 open；原结转凭证只生成红字草稿。`)
  persist()

  return clone(request)
}

export function listReversals(db: MockDatabase) {
  return clone(db.vouchers.filter(row => row.status === 'posted' || row.reversesVoucherId).map(row => ({ ...row, canReverse: row.status === 'posted' && !row.reversedByVoucherId, reversalStatus: row.reversedByVoucherId ? '已生成红字' : row.status === 'posted' ? '可冲销' : '红字草稿' })))
}

export function createReversal(db: MockDatabase, actor: Actor, voucherId: string) {
  requireActorPermission(actor, 'journal_entry:cancel')

  const original = db.vouchers.find(row => row.id === voucherId)
  if (!original)
    throw new Error('原凭证不存在')
  if (original.status !== 'posted')
    throw new Error('只有已过账凭证可以红字冲销')
  if (original.reversedByVoucherId)
    throw new Error('一张原凭证只能有一张有效红字')

  const reversal: VoucherEntity = { id: nextId(db, 'vch'), no: `${original.no}-红字`, period: '2026-11', status: 'draft', debit: original.credit, credit: original.debit, currency: original.currency, summary: `红字冲销 ${original.no}（金额绝对值相同）`, submitter: actor.name, reversesVoucherId: original.id }

  db.vouchers.push(reversal)
  original.reversedByVoucherId = reversal.id
  writeAudit(db, actor, 'voucher_reversal_drafted', 'voucher', reversal.id, `生成红字草稿，原凭证 ${original.no} 保持已过账。`)
  persist()

  return clone(reversal)
}

export function settlementSplit(db: MockDatabase, settlementId: string) {
  const settlement = db.settlements.find(row => row.id === settlementId)
  if (!settlement)
    return null

  return clone({
    ...settlement,
    source: settlement.source ?? (settlement.platform === 'Amazon' ? 'sp_api' : 'file'),
    fxRate: '7.1000',
    payoutAmountFc: '53.50',
    payoutAmountCny: minorFromDecimal('379.8500'),
    differenceCny: minorFromDecimal('1.0700'),
    splitLines: [
      { id: `${settlementId}-sale`, bucket: '销售收入', mapping: 'sales_revenue', amountFc: '53.50', amountCny: minorFromDecimal('379.8500'), status: 'confirmed' },
      { id: `${settlementId}-fx`, bucket: '打款汇差', mapping: 'fx_diff', amountFc: '—', amountCny: minorFromDecimal('1.0700'), status: 'confirmed' },
      { id: `${settlementId}-unknown`, bucket: '未确认映射', mapping: '待人工确认', amountFc: '0.00', amountCny: 0, status: 'suspended' },
    ],
  })
}

export function sourceLabel(source: string) {
  return source === 'sp_api' ? 'API' : source === 'plugin' ? '插件' : '文件'
}
