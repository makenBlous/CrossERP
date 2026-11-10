import { assertPermission, database, delay, readMock } from '@/api/mock-client'
import { accountsPayablePermissionKey } from '@/config/permissions'
import { projectIssues, projectProfit, projectProfitSku, projectRecon, projectVouchers } from '@/mocks/project'
import { submitSuggestion } from '@/mocks/services/approvals'
import { accounts, addFxRate, apAging, apRows, arAging, arRows, cashRows, clearingRows, columnMapDetail, columnMapRows, confirmFeeMap, createVoucherFromIssue, createVoucherFromProfit, exportRows, feeMapRows, fxRates, handleIssue, importDetail, issueDetail, listImports, reconDetail, recordImport, saveColumnMap, settlementDetail, settlements, sourceRow, submitClearing, submitVoucher, voucherDetail } from '@/mocks/services/finance'
import type { CurrencyCode } from '@/types/domain'
import { minorToDecimal } from '@/utils/money'

// 未来: GET /api/v1/finance/profit
export async function fetchProfit() {
  await delay()
  assertPermission('report:read')

  return projectProfit(database().db)
}

export async function fetchProfitSku(internalSku: string, storeId?: string) {
  await delay()
  assertPermission('report:read')

  return projectProfitSku(database().db, internalSku, '2026-10', storeId)
}

// 未来: GET /api/v1/finance/recon-runs
export async function fetchReconRuns() {
  await delay()
  assertPermission('report:read')

  return projectRecon(database().db)
}

// 未来: GET /api/v1/finance/issues
export async function fetchIssues() {
  await delay()
  assertPermission('report:read')

  return projectIssues(database().db)
}

// 未来: GET /api/v1/finance/vouchers
export async function fetchVouchers() {
  await delay()
  assertPermission('journal_entry:read')

  return projectVouchers(database().db)
}

export async function fetchImports() {
  await delay()
  assertPermission('integration:read')

  return readMock(listImports(database().db))
}
export async function fetchImport(id: string) {
  await delay()
  assertPermission('integration:read')

  return readMock(importDetail(database().db, id))
}

export async function uploadImport(fileName: string) {
  const actor = assertPermission('integration:import')
  const row = recordImport(database().db, fileName, actor)

  database().persist()

  return readMock(row)
}
export async function fetchSourceRow(table: string, id: string) {
  await delay()
  assertPermission('integration:read')

  return readMock(sourceRow(table, id))
}
export async function fetchSettlements() {
  await delay()
  assertPermission('report:read')

  return readMock(settlements(database().db))
}
export async function fetchSettlement(id: string) {
  await delay()
  assertPermission('report:read')

  return readMock(settlementDetail(database().db, id))
}
export async function fetchReconDetail(id: string) {
  await delay()
  assertPermission('report:read')

  return readMock(reconDetail(database().db, id))
}
export async function fetchIssueDetail(id: string) {
  await delay()
  assertPermission('report:read')

  return readMock(issueDetail(database().db, id))
}
export async function fetchVoucherDetail(id: string) {
  await delay()
  assertPermission('journal_entry:read')

  return readMock(voucherDetail(database().db, id))
}
export async function fetchAccounts() {
  await delay()
  assertPermission('report:read')

  return readMock(accounts(database().db))
}
export async function fetchFxRates() {
  await delay()
  assertPermission('report:read')

  return readMock(fxRates(database().db))
}

export async function addFxRateEntry(input: { period: string; fromCcy: 'USD' | 'CNY' | 'EUR' | 'GBP' | 'JPY'; toCcy: 'USD' | 'CNY' | 'EUR' | 'GBP' | 'JPY'; rate: string }) {
  const actor = assertPermission('integration:write')
  const row = addFxRate(database().db, input, actor)

  database().persist()

  return readMock(row)
}
export async function fetchFeeMap() {
  await delay()
  assertPermission('integration:read')

  return readMock(feeMapRows(database().db))
}
export async function fetchColumnMaps() {
  await delay()
  assertPermission('integration:read')

  return readMock(columnMapRows(database().db))
}
export async function fetchColumnMap(id: string) {
  await delay()
  assertPermission('integration:read')

  return readMock(columnMapDetail(database().db, id))
}
export async function saveColumnMapEntry(id: string, mappings: Array<{ source: string; field: string }>) {
  const actor = assertPermission('integration:write')
  const row = saveColumnMap(database().db, id, mappings, actor)

  database().persist()

  return readMock(row)
}
export async function fetchAr() {
  await delay()
  assertPermission('report:read')

  return readMock(arRows(database().db))
}
export async function fetchAp() {
  await delay()
  assertPermission(accountsPayablePermissionKey)

  return readMock(apRows(database().db))
}
export async function fetchArAging() {
  await delay()
  assertPermission('report:read')

  return readMock(arAging(database().db))
}
export async function fetchApAging() {
  await delay()
  assertPermission(accountsPayablePermissionKey)

  return readMock(apAging(database().db))
}
export async function fetchClearing() {
  await delay()
  assertPermission('payment_entry:read')

  return readMock(clearingRows(database().db))
}
export async function fetchExports() {
  await delay()
  assertPermission('report:read')

  return readMock(exportRows(database().db))
}
export async function fetchCash() {
  await delay()
  assertPermission('payment_entry:read')

  return readMock(cashRows(database().db))
}
export async function resolveIssue(id: string, action: 'explained' | 'ignored', note: string) {
  const actor = assertPermission('integration:write')

  handleIssue(database().db, id, action, note, actor)
  database().persist()

  return fetchIssueDetail(id)
}
export async function confirmFee(id: string, category: string) {
  const actor = assertPermission('integration:write')

  confirmFeeMap(database().db, id, category, actor)
  database().persist()

  return fetchFeeMap()
}
export async function draftVoucherFromIssue(id: string) {
  const actor = assertPermission('journal_entry:create')
  const row = createVoucherFromIssue(database().db, id, actor)

  database().persist()

  return row
}
export async function draftVoucherFromProfit() {
  const actor = assertPermission('journal_entry:create')
  const row = createVoucherFromProfit(database().db, actor)

  database().persist()

  return row
}
export async function submitClearingApproval(ids: string[] = []) {
  const actor = assertPermission('approval:create')
  const selected = ids.length ? ids : database().db.finance2?.clearing.slice(0, 1).map(item => item.id) ?? []
  const row = submitClearing(database().db, selected, actor)

  database().persist()

  return row
}

export async function submitVoucherApproval(id: string) {
  const actor = assertPermission('journal_entry:submit')
  const row = submitVoucher(database().db, id, actor)

  database().persist()

  return row
}

export async function fetchVoucherApprovalIds(voucherId: string) {
  await delay()
  assertPermission('approval:read')

  return database().db.approvals
    .filter(item => item.targetType === 'voucher' && item.targetId === voucherId)
    .map(item => item.id)
}

/** 利润等 gap-a 草稿提交后，复用已有审批建议入口，不另写一套审批。 */
export async function attachVoucherApproval(voucherId: string, summary: string, amountMinor: number, currency: string) {
  const actor = assertPermission('agent_suggestion:create')
  const pending = database().db.approvals.filter(item => item.targetType === 'voucher' && item.targetId === voucherId && item.status === 'pending')
  if (pending.length)
    return pending.at(-1) ?? null

  const approval = submitSuggestion(database().db, {
    title: summary,
    summary: '借贷合计由服务层校验，审批通过后才生成导出文件。',
    amount: minorToDecimal(amountMinor),
    currency: currency as CurrencyCode,
    storeId: null,
    targetType: 'voucher',
    targetId: voucherId,
  }, actor)

  database().persist()

  return approval
}
