import type { CurrencyCode } from '@/types/domain'

export type GapAPageKey =
  | 'EX01' | 'EX02' | 'EX03' | 'EX04' | 'EX05' | 'EX06' | 'EX07'
  | 'F23' | 'F24' | 'F25' | 'F26' | 'F27' | 'F28' | 'F29' | 'F30' | 'F31' | 'F32' | 'F33' | 'F34'

export type ExpenseClaimStatus = 'draft' | 'submitted' | 'manager_approved' | 'finance_approved' | 'rejected' | 'posted'
export type GapApprovalStatus = 'pending' | 'approved' | 'rejected'

export interface GapAAuditEvent {
  id: string
  at: string
  actor: string
  actorId?: string
  action: string
  detail: string
  origin: 'human' | 'ai'
  agentSuggestionId?: string
}

export interface ExpenseClaimLine {
  id: string
  category: string
  merchant: string
  amount: number
  currency: CurrencyCode
  occurredOn: string
  note: string
}

export interface ExpenseClaim {
  id: string
  claimantId?: string
  claimant: string
  department: string
  status: ExpenseClaimStatus
  total: number
  currency: CurrencyCode
  standardLimit: number
  overStandard: boolean
  attachmentName: string
  origin: 'human' | 'ai'
  lines: ExpenseClaimLine[]
  approvalSteps: Array<{ title: string; status: GapApprovalStatus; actor?: string }>
  budgetPeriod: string
  createdAt: string
}

export interface EmployeeLoan {
  id: string
  claimantId?: string
  claimant: string
  purpose: string
  status: 'draft' | 'submitted' | 'approved' | 'repaid'
  amount: number
  settled: number
  outstanding: number
  currency: CurrencyCode
  dueOn: string
  audit: GapAAuditEvent[]
}

export interface TravelRequest {
  id: string
  claimantId?: string
  claimant: string
  destination: string
  startOn: string
  endOn: string
  budget: number
  currency: CurrencyCode
  status: 'draft' | 'submitted' | 'approved' | 'rejected'
  linkedClaimId?: string
  matchRule?: string
  matchConfirmedAt?: string
}

export interface ExpensePolicy {
  id: string
  category: string
  department: string
  limit: number
  currency: CurrencyCode
  effectiveFrom: string
  active: boolean
  debitAccount?: string
  creditAccount?: string
  mappingNote?: string
}

export interface LedgerEntry {
  id: string
  period: string
  voucherId: string
  account: string
  summary: string
  debit: number
  credit: number
  currency: CurrencyCode
  sourceType: string
  sourceId: string
}

export interface TrialBalanceRow {
  account: string
  opening: number
  debit: number
  credit: number
  closing: number
  currency: CurrencyCode
}

export interface StatementRow {
  account: string
  label: string
  amount: number
  currency: CurrencyCode
  sourceIds: string[]
}

export interface PeriodCloseState {
  period: string
  status: 'open' | 'closing' | 'closed'
  checks: Array<{ id: string; label: string; passed: boolean; detail: string }>
  closedAt?: string
}

export interface CogsRun {
  id: string
  period: string
  outboundCount: number
  amount: number
  currency: CurrencyCode
  status: 'preview' | 'drafted' | 'submitted' | 'posted'
  voucherId?: string
}

export interface BudgetRow {
  id: string
  period: string
  department: string
  account: string
  budget: number
  actual: number
  currency: CurrencyCode
  status: 'normal' | 'warning' | 'exceeded'
}

export interface FxRevaluationRow {
  id: string
  period: string
  currency: CurrencyCode
  closingRate: string
  balance: number
  gainLoss: number
  status: 'preview' | 'drafted' | 'posted'
  voucherId?: string
}

export interface VatReturnRow {
  id: string
  store: string
  period: string
  outputTax: number
  inputTax: number
  payable: number
  dueOn: string
  status: 'draft' | 'ready' | 'submitted'
  currency: CurrencyCode
  submittedAt?: string
}

export interface ExportRebateDocument {
  id: string
  fileName: string
  documentType: '报关单' | '进项发票' | '运输凭证' | '其他'
  size: number
  uploadedAt: string
}

export interface ExportRebateRow {
  id: string
  declarationNo: string
  store: string
  period: string
  inputInvoice: string
  amount: number
  currency: CurrencyCode
  status: 'collecting' | 'ready' | 'submitted' | 'paid'
  dueOn: string
  documents: ExportRebateDocument[]
}

export interface VoucherSourceLink {
  sourceType: 'order' | 'settlement' | 'expense_claim' | 'cogs' | 'profit' | 'fx_revaluation'
  sourceId: string
  label: string
  to: string
  amount: number
  currency: CurrencyCode
}

export interface GapAVoucher {
  id: string
  createdById?: string
  no: string
  period: string
  summary: string
  status: 'draft' | 'pending' | 'approved' | 'rejected' | 'posted'
  debit: number
  credit: number
  currency: CurrencyCode
  debitAccount?: string
  creditAccount?: string
  sourceLinks: VoucherSourceLink[]
  timeline: GapAAuditEvent[]
}

export interface GapAState {
  claims: ExpenseClaim[]
  loans: EmployeeLoan[]
  trips: TravelRequest[]
  policies: ExpensePolicy[]
  ledger: LedgerEntry[]
  periods: PeriodCloseState[]
  cogs: CogsRun[]
  budgets: BudgetRow[]
  fx: FxRevaluationRow[]
  vat: VatReturnRow[]
  rebates: ExportRebateRow[]
  vouchers: GapAVoucher[]
  audits: GapAAuditEvent[]
  orderRules: Array<{ storeId: string; store: string; granularity: 'per_order' | 'per_settlement' | 'per_period_summary' }>
}
