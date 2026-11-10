import { assertPermission, database, delay, readMock } from '@/api/mock-client'
import { activateOpening, approveReopen, balanceOpening, createReopenRequest, createReversal, getOpening, listGlReconcile, listReopenRequests, listReversals, settlementSplit } from '@/mocks/services/fin-gl'
import { useSessionStore } from '@/stores/session'

function actor() {
  const session = useSessionStore()

  return { userId: session.userId, name: session.displayName, role: session.role, at: new Date().toISOString() }
}

export async function fetchGlReconcile() {
  await delay()
  assertPermission('stock_ledger:report')

  return readMock(listGlReconcile())
}

export async function fetchOpening() {
  await delay()
  assertPermission('journal_entry:create')

  return readMock(getOpening())
}

export async function balanceOpeningTrial() {
  const current = actor()
  const row = balanceOpening(database().db, current)

  database().persist()

  return readMock(row)
}

export async function activateOpeningBatch() {
  const current = actor()
  const row = activateOpening(database().db, current)

  database().persist()

  return readMock(row)
}

export async function fetchReopenRequests() {
  await delay()
  assertPermission('period_closing_voucher:cancel')

  return readMock(listReopenRequests())
}

export async function requestPeriodReopen(period: string, reason: string, impact: string) {
  const current = actor()
  const row = createReopenRequest(database().db, current, period, reason, impact)

  database().persist()

  return readMock(row)
}

export async function approvePeriodReopen(requestId: string) {
  const current = actor()
  const row = approveReopen(database().db, current, requestId)

  database().persist()

  return readMock(row)
}

export async function fetchReversalCandidates() {
  await delay()
  assertPermission('journal_entry:write')

  return readMock(listReversals(database().db))
}

export async function draftVoucherReversal(voucherId: string) {
  const current = actor()
  const row = createReversal(database().db, current, voucherId)

  database().persist()

  return readMock(row)
}

export async function fetchSettlementSplit(id: string) {
  await delay()
  assertPermission('payment_reconciliation:read')

  return readMock(settlementSplit(database().db, id))
}
