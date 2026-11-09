import { assertCan, database, delay, readMock } from '@/api/mock-client'
import { projectIssues, projectProfit, projectProfitSku, projectRecon, projectVouchers } from '@/mocks/project'
import { accounts, addFxRate, apAging, apRows, arAging, arRows, cashRows, clearingRows, columnMapDetail, columnMapRows, confirmFeeMap, createVoucherFromIssue, createVoucherFromProfit, exportRows, feeMapRows, fxRates, handleIssue, importDetail, issueDetail, listImports, reconDetail, recordImport, saveColumnMap, settlementDetail, settlements, sourceRow, submitClearing, submitVoucher, voucherDetail } from '@/mocks/services/finance'

// 未来: GET /api/v1/finance/profit
export async function fetchProfit() {
  await delay()

  return projectProfit(database().db)
}

export async function fetchProfitSku(internalSku: string) {
  await delay()

  return projectProfitSku(database().db, internalSku)
}

// 未来: GET /api/v1/finance/recon-runs
export async function fetchReconRuns() {
  await delay()

  return projectRecon(database().db)
}

// 未来: GET /api/v1/finance/issues
export async function fetchIssues() {
  await delay()

  return projectIssues(database().db)
}

// 未来: GET /api/v1/finance/vouchers
export async function fetchVouchers() {
  await delay()

  return projectVouchers(database().db)
}

export async function fetchImports() {
  await delay()

  return readMock(listImports(database().db))
}
export async function fetchImport(id: string) {
  await delay()

  return readMock(importDetail(database().db, id))
}

export async function uploadImport(fileName: string) {
  const actor = assertCan('create')
  const row = recordImport(database().db, fileName, actor)

  database().persist()

  return readMock(row)
}
export async function fetchSourceRow(table: string, id: string) {
  await delay()

  return readMock(sourceRow(table, id))
}
export async function fetchSettlements() {
  await delay()

  return readMock(settlements(database().db))
}
export async function fetchSettlement(id: string) {
  await delay()

  return readMock(settlementDetail(database().db, id))
}
export async function fetchReconDetail(id: string) {
  await delay()

  return readMock(reconDetail(database().db, id))
}
export async function fetchIssueDetail(id: string) {
  await delay()

  return readMock(issueDetail(database().db, id))
}
export async function fetchVoucherDetail(id: string) {
  await delay()

  return readMock(voucherDetail(database().db, id))
}
export async function fetchAccounts() {
  await delay()

  return readMock(accounts(database().db))
}
export async function fetchFxRates() {
  await delay()

  return readMock(fxRates(database().db))
}

export async function addFxRateEntry(input: { period: string; fromCcy: 'USD' | 'CNY' | 'EUR' | 'GBP' | 'JPY'; toCcy: 'USD' | 'CNY' | 'EUR' | 'GBP' | 'JPY'; rate: string }) {
  const actor = assertCan('update')
  const row = addFxRate(database().db, input, actor)

  database().persist()

  return readMock(row)
}
export async function fetchFeeMap() {
  await delay()

  return readMock(feeMapRows(database().db))
}
export async function fetchColumnMaps() {
  await delay()

  return readMock(columnMapRows(database().db))
}
export async function fetchColumnMap(id: string) {
  await delay()

  return readMock(columnMapDetail(database().db, id))
}
export async function saveColumnMapEntry(id: string, mappings: Array<{ source: string; field: string }>) {
  const actor = assertCan('update')
  const row = saveColumnMap(database().db, id, mappings, actor)

  database().persist()

  return readMock(row)
}
export async function fetchAr() {
  await delay()

  return readMock(arRows(database().db))
}
export async function fetchAp() {
  await delay()

  return readMock(apRows(database().db))
}
export async function fetchArAging() {
  await delay()

  return readMock(arAging(database().db))
}
export async function fetchApAging() {
  await delay()

  return readMock(apAging(database().db))
}
export async function fetchClearing() {
  await delay()

  return readMock(clearingRows(database().db))
}
export async function fetchExports() {
  await delay()

  return readMock(exportRows(database().db))
}
export async function fetchCash() {
  await delay()

  return readMock(cashRows(database().db))
}
export async function resolveIssue(id: string, action: 'explained' | 'ignored', note: string) {
  const actor = assertCan('update')

  handleIssue(database().db, id, action, note, actor)
  database().persist()

  return fetchIssueDetail(id)
}
export async function confirmFee(id: string, category: string) {
  const actor = assertCan('update')

  confirmFeeMap(database().db, id, category, actor)
  database().persist()

  return fetchFeeMap()
}
export async function draftVoucherFromIssue(id: string) {
  const actor = assertCan('create')
  const row = createVoucherFromIssue(database().db, id, actor)

  database().persist()

  return row
}
export async function draftVoucherFromProfit() {
  const actor = assertCan('create')
  const row = createVoucherFromProfit(database().db, actor)

  database().persist()

  return row
}
export async function submitClearingApproval(ids: string[] = []) {
  const actor = assertCan('create')
  const selected = ids.length ? ids : database().db.finance2?.clearing.slice(0, 1).map(item => item.id) ?? []
  const row = submitClearing(database().db, selected, actor)

  database().persist()

  return row
}

export async function submitVoucherApproval(id: string) {
  const actor = assertCan('update')
  const row = submitVoucher(database().db, id, actor)

  database().persist()

  return row
}
