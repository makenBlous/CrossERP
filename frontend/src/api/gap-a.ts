import { assertCan, assertPermission, delay } from '@/api/mock-client'
import * as service from '@/mocks/services/gap-a'
import type { CurrencyCode } from '@/types/domain'
import type { ExpenseClaimLine, ExportRebateDocument, GapApprovalStatus } from '@/types/gap-a'
import type { AppAction } from '@/utils/permission'
import { expenseApprovalPermissionKeys } from '@/config/permissions'

function assertAny(actions: AppAction[]) {
  let lastError: unknown

  for (const action of actions) {
    try {
      return assertCan(action)
    }
    catch (error) {
      lastError = error
    }
  }

  throw lastError instanceof Error ? lastError : new Error('当前角色不能执行这个操作')
}

// 未来: GET /api/v1/expense/claims
export async function fetchGapAClaims() {
  await delay()

  return service.listClaims()
}

// 未来: GET /api/v1/expense/claims/{id}
export async function fetchGapAClaim(id: string) {
  await delay()

  return service.claim(id)
}

// 未来: POST /api/v1/expense/claims
export async function createGapAClaim(input: { claimant: string; department: string; attachmentName: string; line: Omit<ExpenseClaimLine, 'id'>; origin: 'human' | 'ai'; agentSuggestionId?: string }) {
  const actor = assertCan('create')

  await delay()

  return service.createClaim({ ...input, claimantId: actor.userId })
}

// 未来: POST /api/v1/expense/claims/{id}/submit
export async function submitGapAClaim(id: string) {
  assertCan('create')
  await delay()

  return service.submitClaim(id)
}

// 未来: POST /api/v1/expense/claims/{id}/decide
export async function decideGapAClaim(id: string, step: 'manager' | 'finance', status: Extract<GapApprovalStatus, 'approved' | 'rejected'>) {
  assertPermission(step === 'manager' ? expenseApprovalPermissionKeys.manager : expenseApprovalPermissionKeys.finance)
  await delay()

  return service.decideClaim(id, step, status)
}

// 未来: GET /api/v1/expense/loans
export async function fetchGapALoans() {
  await delay()

  return service.listLoans()
}

// 未来: GET /api/v1/expense/loans/{id}
export async function fetchGapALoan(id: string) {
  await delay()

  return service.loan(id)
}

// 未来: POST /api/v1/expense/loans/{id}/repay
export async function repayGapALoan(id: string, amount: number) {
  assertPermission('employee_advance:write')
  await delay()

  return service.repayLoan(id, amount)
}

// 未来: POST /api/v1/expense/loans/{id}/offset
export async function offsetGapALoan(id: string, claimId: string) {
  assertPermission('employee_advance:write')
  await delay()

  return service.offsetLoan(id, claimId)
}

// 未来: GET /api/v1/expense/trips
export async function fetchGapATrips() {
  await delay()

  return service.listTrips()
}

// 未来: POST /api/v1/expense/trips
export async function createGapATrip(input: { claimant: string; destination: string; startOn: string; endOn: string; budget: number; currency: CurrencyCode }) {
  const actor = assertCan('create')

  await delay()

  return service.createTrip({ ...input, claimant: actor.name, claimantId: actor.userId })
}

// 未来: POST /api/v1/expense/trips/{id}/submit
export async function submitGapATrip(id: string) {
  assertCan('create')
  await delay()

  return service.submitTrip(id)
}

// 未来: POST /api/v1/expense/trips/{id}/match-suggestion
export async function suggestGapATripClaim(id: string) {
  assertCan('suggest')
  await delay()

  return service.suggestTripClaim(id)
}

// 未来: POST /api/v1/expense/trips/{id}/match
export async function confirmGapATripClaim(id: string, claimId: string) {
  assertCan('update')
  await delay()

  return service.confirmTripClaim(id, claimId)
}

// 未来: GET /api/v1/expense/policies
export async function fetchGapAPolicies() {
  await delay()

  return service.listPolicies()
}

// 未来: PATCH /api/v1/expense/policies/{id}
export async function createGapAPolicy(id: string, limit: number, mapping?: { debitAccount?: string; creditAccount?: string }) {
  assertPermission('expense_claim_type:write')
  await delay()

  return service.savePolicy(id, limit, mapping)
}

// 未来: GET /api/v1/accounting/gl
export async function fetchGapALedger(period?: string) {
  await delay()

  return service.listLedger(period)
}

// 未来: GET /api/v1/accounting/trial-balance
export async function fetchGapATrialBalance(period?: string) {
  await delay()

  return service.trialBalance(period)
}

// 未来: GET /api/v1/accounting/statements/{kind}
export async function fetchGapAStatement(kind: 'income' | 'balance' | 'cashflow', period?: string) {
  await delay()

  return service.statement(kind, period)
}

// 未来: GET /api/v1/accounting/periods
export async function fetchGapAPeriods() {
  await delay()

  return service.listPeriods()
}

// 未来: POST /api/v1/accounting/periods/{period}/close
export async function closeGapAPeriod(period: string) {
  assertCan('approve')
  await delay()

  return service.closePeriod(period)
}

// 未来: GET /api/v1/accounting/cogs-runs
export async function fetchGapACogs() {
  await delay()

  return service.listCogs()
}

// 未来: POST /api/v1/accounting/cogs-runs
export async function createGapACogsVoucher(period: string) {
  assertAny(['create', 'approve'])
  await delay()

  return service.createCogsVoucher(period)
}

// 未来: GET /api/v1/budget/budgets
export async function fetchGapABudgets() {
  await delay()

  return service.listBudgets()
}

// 未来: GET /api/v1/budget/budgets/{id}
export async function fetchGapABudget(id: string) {
  await delay()

  return service.budget(id)
}

// 未来: PATCH /api/v1/budget/budgets/{id}
export async function saveGapABudget(id: string, amount: number) {
  assertPermission('budget:write')
  await delay()

  return service.saveBudget(id, amount)
}

// 未来: GET /api/v1/accounting/fx-revaluations
export async function fetchGapAFx() {
  await delay()

  return service.listFx()
}

// 未来: POST /api/v1/accounting/fx-revaluations/{id}/draft
export async function createGapAFxVoucher(id: string) {
  assertAny(['create', 'approve'])
  await delay()

  return service.createFxVoucher(id)
}

// 未来: GET /api/v1/tax/vat-returns
export async function fetchGapAVat(period?: string) {
  await delay()

  return service.listVat(period)
}

// 未来: POST /api/v1/tax/vat-returns/{id}/submit
export async function submitGapAVat(id: string) {
  assertPermission('vat_return:write')
  await delay()

  return service.submitVat(id)
}

// 未来: GET /api/v1/tax/export-rebates
export async function fetchGapARebates() {
  await delay()

  return service.listRebates()
}

// 未来: POST /api/v1/tax/export-rebates/{id}/documents
export async function uploadGapARebateDocument(id: string, input: Omit<ExportRebateDocument, 'id' | 'uploadedAt'>) {
  assertPermission('export_tax_rebate:write')
  await delay()

  return service.uploadRebateDocument(id, input)
}

// 未来: POST /api/v1/tax/export-rebates/{id}/validate
export async function validateGapARebate(id: string) {
  assertPermission('export_tax_rebate:write')
  await delay()

  return service.validateRebate(id)
}

// 未来: GET /api/v1/finance/vouchers
export async function fetchGapAVouchers() {
  await delay()

  return service.listVouchers()
}

// 未来: GET /api/v1/finance/vouchers/{id}
export async function fetchGapAVoucher(id: string) {
  await delay()

  return service.voucher(id)
}

// 未来: POST /api/v1/finance/vouchers/{id}/submit
export async function submitGapAVoucher(id: string) {
  assertAny(['create', 'approve'])
  await delay()

  return service.submitVoucher(id)
}

// 未来: POST /api/v1/finance/vouchers/{id}/decide
export async function decideGapAVoucher(id: string, approved: boolean) {
  assertCan('approve')
  await delay()

  return service.approveVoucher(id, approved)
}

// 未来: POST /api/v1/finance/vouchers/from-profit
export async function createGapAProfitVoucher(period: string) {
  assertAny(['create', 'approve'])
  await delay()

  return service.createProfitVoucher(period)
}

// 未来: POST /api/v1/finance/vouchers/from-order
export async function generateGapAOrderVoucher(storeId: string, granularity: 'per_order' | 'per_settlement' | 'per_period_summary') {
  assertCan('create')
  await delay()

  return service.generateOrderVoucher(storeId, granularity)
}

// 未来: GET /api/v1/finance/voucher-rules
export async function fetchGapAOrderRules() {
  await delay()

  return service.listOrderRules()
}

// 未来: GET /api/v1/audit/logs?ref_id={id}
export async function fetchGapAAudits(refId?: string) {
  await delay()

  return service.audits(refId)
}
export type GapACurrency = CurrencyCode
