import { database, delay } from '@/api/mock-client'
import { projectIssues, projectProfit, projectRecon, projectVouchers } from '@/mocks/project'

// 未来: GET /api/v1/finance/profit
export async function fetchProfit() {
  await delay()

  return projectProfit(database().db)
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
