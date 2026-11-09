import { assertCan, database, delay } from '@/api/mock-client'
import { projectApprovals } from '@/mocks/project'
import { approvalPayloadHash } from '@/mocks/services/approvals'
import type { ApprovalStatus } from '@/types/domain'

async function withPayloadHashes() {
  const db = database().db
  const projected = projectApprovals(db)

  return Promise.all(projected.map(async item => ({
    ...item,
    payloadHash: await approvalPayloadHash(db.approvals.find(approval => approval.id === item.id)! ),
  })))
}

// 未来: GET /api/v1/approvals
export async function fetchApprovals() {
  await delay()

  return withPayloadHashes()
}

export async function fetchApproval(id: string) {
  await delay()

  return (await withPayloadHashes()).find(item => item.id === id) ?? null
}

export async function fetchSubmittedApprovals() {
  await delay()

  return (await withPayloadHashes()).filter(item => item.submitter === '林夏' || item.status !== 'pending')
}

// 未来: POST /api/v1/approvals/{id}/decide
export async function decideApproval(id: string, status: Extract<ApprovalStatus, 'approved' | 'rejected'>, comment = '') {
  await delay()

  const actor = assertCan('approve')

  database().decide(id, status, actor, comment)

  return (await withPayloadHashes()).find(item => item.id === id) ?? null
}
