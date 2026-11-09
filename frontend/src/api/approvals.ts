import { assertCan, database, delay } from '@/api/mock-client'
import { projectApprovals } from '@/mocks/project'
import type { ApprovalStatus } from '@/types/domain'

// 未来: GET /api/v1/approvals
export async function fetchApprovals() {
  await delay()

  return projectApprovals(database().db)
}

export async function fetchApproval(id: string) {
  await delay()

  return projectApprovals(database().db).find(item => item.id === id) ?? null
}

export async function fetchSubmittedApprovals() {
  await delay()

  return projectApprovals(database().db).filter(item => item.submitter === '林夏' || item.status !== 'pending')
}

// 未来: POST /api/v1/approvals/{id}/decide
export async function decideApproval(id: string, status: Extract<ApprovalStatus, 'approved' | 'rejected'>, comment = '') {
  await delay()

  const actor = assertCan('approve')

  database().decide(id, status, actor, comment)

  return projectApprovals(database().db).find(item => item.id === id) ?? null
}
