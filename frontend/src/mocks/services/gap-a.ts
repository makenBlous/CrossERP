/* eslint-disable max-statements-per-line, sonarjs/no-same-line-conditional, @typescript-eslint/no-shadow */
import type {
  BudgetRow, CogsRun, EmployeeLoan, ExpenseClaim, ExpenseClaimLine, ExpensePolicy, ExportRebateDocument, ExportRebateRow, FxRevaluationRow,
  GapAAuditEvent, GapAState, GapAVoucher, GapApprovalStatus, LedgerEntry, PeriodCloseState, StatementRow, TravelRequest,
  TrialBalanceRow, VatReturnRow, VoucherSourceLink,
} from '@/types/gap-a'
import { demoIdentities, useSessionStore } from '@/stores/session'
import { minorFromDecimal } from '@/utils/money'

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T
const now = () => new Date().toISOString()
const actor = () => useSessionStore().displayName
const actorId = () => useSessionStore().userId

function identityIdForName(name: string) {
  const identity = Object.values(demoIdentities).find(item => item.name === name)

  return identity?.id
}

function audit(id: string, action: string, detail: string, origin: 'human' | 'ai' = 'human', agentSuggestionId?: string): GapAAuditEvent {
  return { id, at: now(), actor: actor(), action, detail, origin, agentSuggestionId }
}

const seedAudit = (id: string): GapAAuditEvent[] => [
  { id: `${id}-draft`, at: '2026-10-31T09:00:00Z', actor: '演示运营', action: '起草', detail: '按已存确定性金额生成凭证草稿。', origin: 'human' },
  { id: `${id}-submit`, at: '2026-11-01T10:00:00Z', actor: '演示运营', action: '提交审批', detail: '借贷合计校验通过，提交统一审批中心。', origin: 'human' },
  { id: `${id}-approve`, at: '2026-11-02T11:00:00Z', actor: '演示财务', action: '批准', detail: '财务复核通过，保留审计记录。', origin: 'human' },
]

function makeLine(id: string, amount: number, category = '交通'): ExpenseClaimLine {
  return { id, category, merchant: category === '交通' ? '上海虹桥机场' : '演示商户', amount, currency: 'CNY', occurredOn: '2026-11-05', note: '演示费用，金额来自票面' }
}

function initialState(): GapAState {
  const vch1: GapAVoucher = {
    id: 'vch-1',
    createdById: 'demo-operator',
    no: '记-2026-10-018',
    period: '2026-10',
    summary: '10 月收入与费用草稿',
    status: 'draft',
    debit: minorFromDecimal('42856'),
    credit: minorFromDecimal('42856'),
    currency: 'CNY',
    sourceLinks: [
      { sourceType: 'settlement', sourceId: 'stl-us-2026-10', label: 'Amazon US 结算单 STL-US-2026-10', to: '/finance/settlements/stl-us-2026-10', amount: minorFromDecimal('42856'), currency: 'CNY' },
      { sourceType: 'order', sourceId: 'ord-1001', label: '订单 ORDER-110-1000001-2000001', to: '/orders/ord-1001', amount: minorFromDecimal('12840'), currency: 'CNY' },
    ],
    timeline: seedAudit('vch-1'),
  }

  const vch2: GapAVoucher = {
    id: 'vch-2',
    createdById: 'demo-operator',
    no: '记-2026-10-019',
    period: '2026-10',
    summary: '帐篷成本结转，待财务审批',
    status: 'pending',
    debit: minorFromDecimal('18640.2'),
    credit: minorFromDecimal('18640.2'),
    currency: 'CNY',
    sourceLinks: [{ sourceType: 'cogs', sourceId: 'cogs-001', label: '10 月成本结转', to: '/finance/cogs', amount: minorFromDecimal('18640.2'), currency: 'CNY' }],
    timeline: [
      { id: 'vch-2-submit', at: '2026-11-03T09:00:00Z', actor: '演示运营', action: '提交审批', detail: '成本结转草稿待财务审批。', origin: 'human' },
    ],
  }

  return {
    claims: [{ id: 'exp-001', claimantId: 'demo-employee', claimant: '演示普通员工', department: '运营部', status: 'submitted', total: minorFromDecimal('850'), currency: 'CNY', standardLimit: minorFromDecimal('600'), overStandard: true, attachmentName: '差旅发票-001.pdf', origin: 'human', lines: [makeLine('exp-001-1', minorFromDecimal('850'))], approvalSteps: [{ title: '部门主管', status: 'pending' }, { title: '财务', status: 'pending' }], budgetPeriod: '2026-11', createdAt: '2026-11-05T09:00:00Z' }],
    loans: [{ id: 'loan-001', claimant: '演示普通员工', purpose: '海外展会差旅备用金', status: 'approved', amount: minorFromDecimal('3000'), settled: minorFromDecimal('1200'), outstanding: minorFromDecimal('1800'), currency: 'CNY', dueOn: '2026-12-15', audit: [{ id: 'loan-001-approved', at: '2026-10-20T09:00:00Z', actor: '演示财务', action: '批准借款', detail: '借款审批通过。', origin: 'human' }] }],
    trips: [{ id: 'trip-001', claimant: '演示普通员工', destination: '深圳', startOn: '2026-11-18', endOn: '2026-11-20', budget: minorFromDecimal('2400'), currency: 'CNY', status: 'approved' }],
    policies: [{ id: 'policy-transport', category: '交通', department: '运营部', limit: minorFromDecimal('600'), currency: 'CNY', effectiveFrom: '2026-01-01', active: true }, { id: 'policy-hotel', category: '住宿', department: '全公司', limit: minorFromDecimal('800'), currency: 'CNY', effectiveFrom: '2026-01-01', active: true }, { id: 'policy-meal', category: '餐补', department: '全公司', limit: minorFromDecimal('150'), currency: 'CNY', effectiveFrom: '2026-01-01', active: true }],
    ledger: [
      { id: 'gl-001', period: '2026-09', voucherId: 'vch-3', account: '主营业务收入', summary: '9 月利润凭证', debit: 0, credit: minorFromDecimal('96220'), currency: 'CNY', sourceType: 'profit', sourceId: '2026-09' },
      { id: 'gl-002', period: '2026-09', voucherId: 'vch-3', account: '平台结算清算', summary: '9 月利润凭证', debit: minorFromDecimal('96220'), credit: 0, currency: 'CNY', sourceType: 'profit', sourceId: '2026-09' },
      { id: 'gl-003', period: '2026-10', voucherId: 'vch-2', account: '主营业务成本', summary: '帐篷成本结转', debit: minorFromDecimal('18640.2'), credit: 0, currency: 'CNY', sourceType: 'cogs', sourceId: 'cogs-001' },
      { id: 'gl-004', period: '2026-10', voucherId: 'vch-2', account: '库存商品', summary: '帐篷成本结转', debit: 0, credit: minorFromDecimal('18640.2'), currency: 'CNY', sourceType: 'cogs', sourceId: 'cogs-001' },
    ],
    periods: [{ period: '2026-09', status: 'open', checks: [{ id: 'pending', label: '未审批凭证', passed: true, detail: '无未审批凭证' }, { id: 'balance', label: '借贷平衡', passed: true, detail: '借贷相等' }] }, { period: '2026-10', status: 'open', checks: [{ id: 'pending', label: '未审批凭证', passed: false, detail: '存在待审批凭证 vch-2' }, { id: 'balance', label: '借贷平衡', passed: true, detail: '借贷相等' }] }],
    cogs: [{ id: 'cogs-001', period: '2026-10', outboundCount: 24, amount: minorFromDecimal('18640.2'), currency: 'CNY', status: 'preview', voucherId: 'vch-2' }],
    budgets: [{ id: 'budget-2026-11-ops', period: '2026-11', department: '运营部', account: '差旅费', budget: minorFromDecimal('10000'), actual: minorFromDecimal('8200'), currency: 'CNY', status: 'warning' }, { id: 'budget-2026-11-fin', period: '2026-11', department: '财务部', account: '办公费', budget: minorFromDecimal('12000'), actual: minorFromDecimal('3600'), currency: 'CNY', status: 'normal' }],
    fx: [{ id: 'fxr-001', period: '2026-10', currency: 'USD', closingRate: '7.12000000', balance: minorFromDecimal('12800'), gainLoss: minorFromDecimal('220.5'), status: 'preview' }, { id: 'fxr-002', period: '2026-10', currency: 'EUR', closingRate: '7.78000000', balance: minorFromDecimal('6200'), gainLoss: minorFromDecimal('-84.2'), status: 'preview' }],
    vat: [{ id: 'vat-001', store: 'Northwind Outdoor DE', period: '2026-Q4', outputTax: minorFromDecimal('2180'), inputTax: minorFromDecimal('920'), payable: minorFromDecimal('1260'), dueOn: '2027-01-31', status: 'ready', currency: 'EUR' }, { id: 'vat-002', store: 'Northwind Outdoor UK', period: '2026-Q4', outputTax: minorFromDecimal('1850'), inputTax: minorFromDecimal('1100'), payable: minorFromDecimal('750'), dueOn: '2027-01-31', status: 'draft', currency: 'GBP' }],
    rebates: [{ id: 'rebate-001', declarationNo: 'DECL-2026-10-018', store: 'Northwind Outdoor US', period: '2026-10', inputInvoice: 'INV-2026-10-088', amount: minorFromDecimal('4860'), currency: 'CNY', status: 'collecting', dueOn: '2026-12-31', documents: [] }],
    vouchers: [vch1, vch2, { id: 'vch-3', createdById: 'demo-operator', no: '记-2026-09-011', period: '2026-09', summary: '9 月利润凭证', status: 'posted', debit: minorFromDecimal('96220'), credit: minorFromDecimal('96220'), currency: 'CNY', sourceLinks: [{ sourceType: 'profit', sourceId: '2026-09', label: '2026-09 利润快照', to: '/finance/profit', amount: minorFromDecimal('96220'), currency: 'CNY' }], timeline: seedAudit('vch-3') }],
    audits: [...seedAudit('vch-1'), ...seedAudit('vch-3')],
    orderRules: [{ storeId: 'amz-us', store: 'Northwind Outdoor US', granularity: 'per_settlement' }, { storeId: 'amz-uk', store: 'Northwind Outdoor UK', granularity: 'per_period_summary' }, { storeId: 'shopify', store: 'northwind-outdoor.com', granularity: 'per_order' }],
  }
}

const STORAGE_KEY = 'crosserp-gap-a-state'
let state: GapAState

function loadState() {
  if (typeof localStorage === 'undefined')
    return initialState()

  try {
    const saved = localStorage.getItem(STORAGE_KEY)

    if (!saved)
      return initialState()

    const parsed = JSON.parse(saved) as GapAState

    parsed.rebates = parsed.rebates.map(item => ({ ...item, documents: item.documents ?? [] }))
    parsed.claims = parsed.claims.map(item => ({
      ...item,
      claimantId: item.claimantId ?? identityIdForName(item.claimant),
    }))
    parsed.vouchers = parsed.vouchers.map(item => ({
      ...item,
      createdById: item.createdById ?? 'demo-operator',
    }))

    return parsed
  }
  catch {
    return initialState()
  }
}

function persist() {
  if (typeof localStorage !== 'undefined')
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

state = loadState()

export function resetGapA() { state = initialState(); persist() }
export function gapAState() { return clone(state) }
export function listClaims() { return clone(state.claims) }
export function claim(id: string) { return clone(state.claims.find(item => item.id === id) ?? null) }
export function listLoans() { return clone(state.loans) }
export function loan(id: string) { return clone(state.loans.find(item => item.id === id) ?? null) }
export function listTrips() { return clone(state.trips) }
export function createTrip(input: Omit<TravelRequest, 'id' | 'status'>) {
  const item: TravelRequest = { ...input, id: nextId('trip'), status: 'draft' }

  state.trips.unshift(item)
  addAudit(audit('trip-created', '创建差旅申请', `创建差旅申请 ${item.id}，预算由代码按申请填写保存。`), item.id)
  persist()

  return clone(item)
}
export function submitTrip(id: string) {
  const item = state.trips.find(row => row.id === id)
  if (!item)
    return null
  if (item.status !== 'draft')
    throw new Error('只有草稿差旅申请可以提交')

  item.status = 'submitted'
  addAudit(audit('trip-submitted', '提交差旅申请', `差旅申请 ${id} 已进入人工审批。`), id)
  persist()

  return clone(item)
}
export function suggestTripClaim(id: string) {
  const item = state.trips.find(row => row.id === id)
  if (!item)
    return null

  const start = item.startOn.slice(0, 10)
  const end = item.endOn.slice(0, 10)

  const candidates = state.claims
    .map(claimItem => {
      const sameClaimant = claimItem.claimant === item.claimant
      const inWindow = claimItem.lines.some(line => line.occurredOn >= start && line.occurredOn <= end)
      const withinBudget = claimItem.total <= item.budget
      const score = (sameClaimant ? 100 : 0) + (inWindow ? 50 : 0) + (withinBudget ? 20 : 0)

      return { claim: claimItem, score }
    })
    .filter(candidate => candidate.score > 0)
    .sort((left, right) => right.score - left.score || left.claim.id.localeCompare(right.claim.id))

  const best = candidates[0]
  if (!best)
    throw new Error('没有找到符合差旅人、日期或预算规则的报销单')

  addAudit(audit('trip-match-suggested', '模拟匹配建议', `按人员、日期窗口、预算规则建议关联报销 ${best.claim.id}，等待人工确认。`), id)
  persist()

  return clone({ trip: item, claim: best.claim, score: best.score, rule: '同人员优先，其次日期在出差窗口内，且报销金额不超过预算' })
}
export function confirmTripClaim(id: string, claimId: string) {
  const item = state.trips.find(row => row.id === id)
  const claimItem = state.claims.find(row => row.id === claimId)
  if (!item || !claimItem)
    return null

  item.linkedClaimId = claimId
  item.matchRule = '人工确认：同人员/日期窗口/预算规则候选，可人工改选'
  item.matchConfirmedAt = now()
  addAudit(audit('trip-match-confirmed', '确认差旅匹配', `人工确认差旅 ${id} 关联报销 ${claimId}。`), id)
  persist()

  return clone(item)
}
export function listPolicies() { return clone(state.policies) }
export function savePolicy(id: string, limit: number) {
  const item = state.policies.find(row => row.id === id)
  if (!item || limit <= 0)
    return null
  item.limit = limit
  persist()

  return clone(item)
}
export function listLedger(period?: string) { return clone(state.ledger.filter(item => !period || item.period === period)) }
export function listVouchers() { return clone(state.vouchers) }
export function voucher(id: string) { return clone(state.vouchers.find(item => item.id === id) ?? null) }
export function listBudgets() { return clone(state.budgets) }
export function budget(id: string) { return clone(state.budgets.find(item => item.id === id) ?? null) }
export function listCogs() { return clone(state.cogs) }
export function listFx() { return clone(state.fx) }
export function listVat(period?: string) { return clone(state.vat.filter(item => !period || item.period === period)) }
export function submitVat(id: string) {
  const item = state.vat.find(row => row.id === id)
  if (!item)
    return null
  if (item.status === 'submitted')
    return clone(item)
  if (item.status === 'draft')
    item.status = 'ready'
  item.status = 'submitted'
  item.submittedAt = now()
  addAudit(audit('vat-submitted', '保存模拟 VAT 申报', `VAT ${id} 已保存为模拟申报记录，期间 ${item.period}。`), id)
  persist()

  return clone(item)
}
export function listRebates() { return clone(state.rebates) }
export function uploadRebateDocument(id: string, input: Omit<ExportRebateDocument, 'id' | 'uploadedAt'>) {
  const item = state.rebates.find(row => row.id === id)
  if (!item)
    return null
  const document: ExportRebateDocument = { ...input, id: nextId('rebate-doc'), uploadedAt: now() }

  item.documents.push(document)
  if (['报关单', '进项发票', '运输凭证'].every(type => item.documents.some(row => row.documentType === type)))
    item.status = 'ready'
  addAudit(audit('rebate-document-uploaded', '模拟上传退税资料', `仅登记文件元数据：${document.fileName}（${document.documentType}，${document.size} 字节）。`), id)
  persist()

  return clone(item)
}
export function validateRebate(id: string) {
  const item = state.rebates.find(row => row.id === id)
  if (!item)
    return null
  const required = ['报关单', '进项发票', '运输凭证'] as const
  const missing = required.filter(type => !item.documents.some(row => row.documentType === type))
  if (!missing.length)
    item.status = 'ready'
  addAudit(audit('rebate-validated', '校验出口退税资料', missing.length ? `资料不齐全，缺少：${missing.join('、')}。` : '资料齐全，状态更新为待申报。'), id)
  persist()

  return clone({ item, missing })
}
export function listPeriods() { return clone(state.periods) }
export function listOrderRules() { return clone(state.orderRules) }
export function audits(refId?: string) { return clone(refId ? state.audits.filter(item => item.id.startsWith(refId) || item.detail.includes(refId)) : state.audits) }

function nextId(prefix: string) { return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}` }
function addAudit(event: GapAAuditEvent, refId: string) {
  state.audits.push({ ...event, id: `${refId}-${event.id}` })

  const item = state.vouchers.find(row => row.id === refId); if (item)
    item.timeline.push({ ...event, id: `${refId}-${event.id}` })
}
function assertOpen(period: string) {
  if (state.periods.find(item => item.period === period)?.status === 'closed')
    throw new Error(`期间 ${period} 已结账，不能生成凭证`)
}

function expenseAccountForCategory(lines: ExpenseClaimLine[]) {
  const category = lines[0]?.category ?? '其他'
  const salesCategories = ['广告', '销售', '推广', '佣金']

  return `${salesCategories.some(keyword => category.includes(keyword)) ? '销售费用' : '管理费用'}-${category}费`
}

export function createClaim(input: { claimant: string; claimantId?: string; department: string; attachmentName: string; line: Omit<ExpenseClaimLine, 'id'>; origin: 'human' | 'ai'; agentSuggestionId?: string }) {
  const id = `exp-${String(state.claims.length + 1).padStart(3, '0')}`
  const line = { ...input.line, id: `${id}-1` }
  const policy = state.policies.find(item => item.category === line.category && (item.department === input.department || item.department === '全公司'))
  const item: ExpenseClaim = { id, claimantId: input.claimantId ?? identityIdForName(input.claimant), claimant: input.claimant, department: input.department, status: 'draft', total: line.amount, currency: line.currency, standardLimit: policy?.limit ?? line.amount, overStandard: line.amount > (policy?.limit ?? line.amount), attachmentName: input.attachmentName, origin: input.origin, lines: [line], approvalSteps: [{ title: '部门主管', status: 'pending' }, { title: '财务', status: 'pending' }], budgetPeriod: '2026-11', createdAt: now() }

  state.claims.unshift(item)
  addAudit(audit('claim-created', '创建报销草稿', `创建报销 ${id}，金额由票面和代码合计。`, input.origin, input.agentSuggestionId), id)
  persist()

  return clone(item)
}

export function submitClaim(id: string) {
  const item = state.claims.find(row => row.id === id); if (!item)
    return null
  if (item.origin === 'ai')
    throw new Error('AI 来源只能保存草稿，提交审批须由人工重新确认')
  if (item.status === 'rejected')
    throw new Error('已驳回的报销不能继续提交审批')
  if (item.overStandard)
    throw new Error('费用超过标准，请调整明细或补充人工说明后再提交')
  item.status = 'submitted'; addAudit(audit('claim-submitted', '提交报销', '进入部门主管审批。'), id)
  persist()

  return clone(item)
}

export function decideClaim(id: string, step: 'manager' | 'finance', status: Extract<GapApprovalStatus, 'approved' | 'rejected'>) {
  const item = state.claims.find(row => row.id === id); if (!item)
    return null
  if (item.origin === 'ai')
    throw new Error('AI 来源只能保存草稿，不能审批')
  if (item.status === 'rejected')
    throw new Error('已驳回的报销不能继续审批')
  const currentActor = actor(); if (item.claimantId && actorId() === item.claimantId)
    throw new Error('不能审批自己提交的报销单，请换另一位审批人')
  const index = step === 'manager' ? 0 : 1
  if (item.approvalSteps[index].status !== 'pending')
    throw new Error('该审批步骤已经处理，不能重复审批')
  if (step === 'manager' && item.status !== 'submitted')
    throw new Error('只有已提交的报销单才能由主管审批')
  if (step === 'finance' && item.status !== 'manager_approved')
    throw new Error('主管审批通过后，财务才能审批')

  item.approvalSteps[index].status = status; item.approvalSteps[index].actor = currentActor
  if (status === 'rejected') { item.status = 'rejected' }
  else if (step === 'manager') { item.status = 'manager_approved' }
  else {
    const amount = item.lines.reduce((sum, line) => sum + line.amount, 0)

    item.total = amount
    item.status = 'finance_approved'; item.status = 'posted'

    const budget = state.budgets.find(row => row.period === item.budgetPeriod && row.department === item.department)
    if (budget) { budget.actual += item.total; budget.status = budget.actual >= budget.budget ? 'exceeded' : budget.actual >= budget.budget * 0.8 ? 'warning' : 'normal' }
    if (!state.vouchers.some(voucher => voucher.sourceLinks.some(link => link.sourceType === 'expense_claim' && link.sourceId === id)))
      createVoucher(`报销 ${id} 凭证草稿`, item.budgetPeriod, amount, [{ sourceType: 'expense_claim', sourceId: id, label: `报销单 ${id}`, to: `/expense/claims/${id}`, amount, currency: item.currency }], 'expense_claim', id, expenseAccountForCategory(item.lines), '其他应付款-员工')
  }
  addAudit(audit(`claim-${step}-${status}`, status === 'approved' ? '批准报销' : '驳回报销', `${step === 'manager' ? '部门主管' : '财务'}${status === 'approved' ? '批准' : '驳回'} ${id}。`), id)
  persist()

  return clone(item)
}

export function repayLoan(id: string, amount: number) {
  const item = state.loans.find(row => row.id === id); if (!item || amount <= 0)
    return null; item.settled = Math.min(item.amount, item.settled + amount); item.outstanding = item.amount - item.settled; if (item.outstanding === 0)
    item.status = 'repaid'; addAudit(audit('loan-repay', '登记还款', `登记还款 ${amount / 10000} CNY。`), id)
  persist()

  return clone(item)
}
export function offsetLoan(loanId: string, claimId: string) {
  const loanItem = state.loans.find(row => row.id === loanId); const claimItem = state.claims.find(row => row.id === claimId); if (!loanItem || !claimItem)
    return null; const amount = Math.min(loanItem.outstanding, claimItem.total)

  loanItem.settled += amount; loanItem.outstanding -= amount; if (!loanItem.outstanding)
    loanItem.status = 'repaid'; addAudit(audit('loan-offset', '冲抵报销', `报销 ${claimId} 冲抵借款 ${loanId}。`), loanId)
  persist()

  return clone(loanItem)
}

export function createVoucher(summary: string, period: string, amount: number, sourceLinks: VoucherSourceLink[], sourceType: string, sourceId: string, debitAccount = '主营业务成本', creditAccount = '平台结算清算', createdById = actorId()) {
  assertOpen(period)

  const id = nextId('vch'); const item: GapAVoucher = { id, createdById, no: `记-${period}-${String(state.vouchers.length + 20).padStart(3, '0')}`, period, summary, status: 'draft', debit: amount, credit: amount, currency: 'CNY', debitAccount, creditAccount, sourceLinks, timeline: [audit('draft', '起草', `按 ${sourceType} ${sourceId} 的已存金额生成凭证草稿。`)] }

  state.vouchers.unshift(item); state.ledger.push({ id: nextId('gl'), period, voucherId: id, account: debitAccount, summary, debit: amount, credit: 0, currency: 'CNY', sourceType, sourceId }, { id: nextId('gl'), period, voucherId: id, account: creditAccount, summary, debit: 0, credit: amount, currency: 'CNY', sourceType, sourceId }); addAudit(audit('voucher-created', '创建凭证草稿', summary), id)
  persist()

  return clone(item)
}

export function submitVoucher(id: string) {
  const item = state.vouchers.find(row => row.id === id); if (!item || item.status !== 'draft')
    return null; item.status = 'pending'; addAudit(audit('submit', '提交审批', '借贷平衡检查通过，进入审批中心。'), id)
  persist()

  return clone(item)
}
export function approveVoucher(id: string, approved: boolean) {
  const item = state.vouchers.find(row => row.id === id); if (!item)
    return null; if (item.createdById && actorId() === item.createdById)
    throw new Error('不能审批自己提交的凭证'); if (item.status !== 'pending')
    throw new Error(item.status === 'rejected' ? '已驳回的凭证不能继续审批' : '只有待审批凭证才能审批'); item.status = approved ? 'approved' : 'rejected'; addAudit(audit(approved ? 'approve' : 'reject', approved ? '批准' : '驳回', approved ? '凭证审批通过，可进入总账。' : '凭证审批未通过。'), id)
  persist()

  return clone(item)
}
export function createProfitVoucher(period: string) {
  const amount = period === '2026-09' ? minorFromDecimal('96220') : minorFromDecimal('42856')

  return createVoucher(`${period} 利润凭证`, period, amount, [{ sourceType: 'profit', sourceId: period, label: `${period} 利润快照`, to: '/finance/profit', amount, currency: 'CNY' }], 'profit', period)
}
export function generateOrderVoucher(storeId: string, granularity: 'per_order' | 'per_settlement' | 'per_period_summary') {
  const rule = state.orderRules.find(row => row.storeId === storeId); if (rule)
    rule.granularity = granularity; const amount = granularity === 'per_order' ? minorFromDecimal('12840') : granularity === 'per_settlement' ? minorFromDecimal('42856') : minorFromDecimal('85712'); const links: VoucherSourceLink[] = granularity === 'per_order' ? [{ sourceType: 'order', sourceId: 'ord-1001', label: '订单 ORDER-110-1000001-2000001', to: '/orders/ord-1001', amount, currency: 'CNY' }] : [{ sourceType: 'settlement', sourceId: 'stl-us-2026-10', label: '结算单 STL-US-2026-10', to: '/finance/settlements/stl-us-2026-10', amount, currency: 'CNY' }, { sourceType: 'order', sourceId: 'ord-1001', label: '订单 ORDER-110-1000001-2000001', to: '/orders/ord-1001', amount: minorFromDecimal('12840'), currency: 'CNY' }]

  return createVoucher(`订单收入 / ${granularity}`, '2026-10', amount, links, 'sales_order', storeId)
}
export function createCogsVoucher(period: string) {
  const run = state.cogs.find(row => row.period === period); if (!run)
    return null; const voucher = createVoucher(`${period} 成本结转`, period, run.amount, [{ sourceType: 'cogs', sourceId: run.id, label: `${period} 已确认出库 ${run.outboundCount} 笔`, to: '/finance/cogs', amount: run.amount, currency: run.currency }], 'cogs', run.id)

  run.status = 'drafted'; run.voucherId = voucher.id
  persist()

  return clone(voucher)
}
export function createFxVoucher(id: string) {
  const row = state.fx.find(item => item.id === id); if (!row)
    return null; const amount = Math.abs(row.gainLoss); const voucher = createVoucher(`${row.period} ${row.currency} 汇兑重估`, row.period, amount, [{ sourceType: 'fx_revaluation', sourceId: row.id, label: `${row.currency} 汇兑重估`, to: '/finance/fx-revaluation', amount, currency: 'CNY' }], 'fx_revaluation', row.id)

  row.status = 'drafted'; row.voucherId = voucher.id
  persist()

  return clone(voucher)
}

export function trialBalance(period = '2026-10'): TrialBalanceRow[] {
  const by = new Map<string, TrialBalanceRow>()

  state.ledger.filter(row => row.period === period).forEach(row => {
    const item = by.get(row.account) ?? { account: row.account, opening: 0, debit: 0, credit: 0, closing: 0, currency: 'CNY' as const }

    item.debit += row.debit; item.credit += row.credit; item.closing = item.opening + item.debit - item.credit; by.set(row.account, item)
  })

  return clone([...by.values()])
}
export function statement(kind: 'income' | 'balance' | 'cashflow', period = '2026-10'): StatementRow[] {
  const rows = trialBalance(period); if (kind === 'income')
    return clone(rows.filter(row => row.account.includes('收入') || row.account.includes('成本')).map(row => ({ account: row.account, label: row.account, amount: row.credit - row.debit, currency: 'CNY' as const, sourceIds: state.ledger.filter(item => item.period === period && item.account === row.account).map(item => item.sourceId) }))); if (kind === 'cashflow')
    return clone([{ account: '经营活动现金流', label: '经营活动现金流', amount: rows.reduce((sum, row) => sum + row.credit - row.debit, 0), currency: 'CNY' as const, sourceIds: state.ledger.filter(item => item.period === period).map(item => item.voucherId) }])

  return clone(rows.filter(row => row.account.includes('库存') || row.account.includes('清算')).map(row => ({ account: row.account, label: row.account, amount: row.closing, currency: 'CNY' as const, sourceIds: state.ledger.filter(item => item.period === period && item.account === row.account).map(item => item.sourceId) })))
}

export function closePeriod(period: string) {
  const item = state.periods.find(row => row.period === period); if (!item)
    return null; const hasPending = state.vouchers.some(row => row.period === period && row.status === 'pending')

  item.checks[0].passed = !hasPending; item.checks[0].detail = hasPending ? '存在待审批凭证，不能结账' : '无未审批凭证'; if (hasPending)
    throw new Error('有未审批凭证，不能结账'); item.status = 'closed'; item.closedAt = now(); item.checks.forEach(check => { check.passed = true })
  persist()

  return clone(item)
}
export function saveBudget(id: string, budget: number) {
  const item = state.budgets.find(row => row.id === id); if (!item)
    return null; item.budget = budget; item.status = item.actual >= budget ? 'exceeded' : item.actual >= budget * 0.8 ? 'warning' : 'normal'; addAudit(audit('budget-update', '调整预算', `预算调整为 ${budget / 10000} CNY。`), id)
  persist()

  return clone(item)
}

export type GapATableRow = ExpenseClaim | EmployeeLoan | TravelRequest | ExpensePolicy | LedgerEntry | BudgetRow | CogsRun | FxRevaluationRow | VatReturnRow | ExportRebateRow | GapAVoucher | PeriodCloseState
