import { assertCan, database, delay } from '@/api/mock-client'
import { projectApprovals } from '@/mocks/project'
import type { ApprovalStatus } from '@/types/domain'

// 未来: GET /api/v1/approvals
export async function fetchApprovals() {
  await delay()

  return projectApprovals(database().db)
}

// 未来: POST /api/v1/approvals/{id}/decide
export async function decideApproval(id: string, status: Extract<ApprovalStatus, 'approved' | 'rejected'>) {
  await delay()

  const actor = assertCan('approve')

  database().decide(id, status, actor)

  return projectApprovals(database().db).find(item => item.id === id) ?? null
}
