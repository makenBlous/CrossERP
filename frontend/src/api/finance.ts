import { readMock } from '@/api/mock-client'
import { issues, profitRows, reconRuns, storeProfits, vouchers } from '@/mocks/finance'

export function fetchProfit() {
  return readMock({ rows: profitRows, stores: storeProfits })
}

export function fetchReconRuns() {
  return readMock(reconRuns)
}

export function fetchIssues() {
  return readMock(issues)
}

export function fetchVouchers() {
  return readMock(vouchers)
}
