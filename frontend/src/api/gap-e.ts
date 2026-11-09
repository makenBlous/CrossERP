/* eslint-disable max-statements-per-line */
import { assertCan, currentActor, database, delay, readMock } from '@/api/mock-client'
import * as service from '@/mocks/services/gap-e'
import type { EmployeeFile, KbAccessLog, KbDocument, KbExpiryItem, KbQaItem, KbReviewItem, KbSearchResult, KbSpace, KbVersion, OnboardingAnswer, OnboardingChecklistItem } from '@/types/gap-e'

// 未来: GET /api/v1/kb/spaces
export async function fetchKbSpaces(): Promise<KbSpace[]> {
  await delay()

  return readMock(service.listSpaces(database().db, currentActor()))
}

// 未来: GET /api/v1/kb/spaces/{id}
export async function fetchKbSpace(id: string): Promise<KbSpace | null> {
  await delay()

  return readMock(service.getSpace(database().db, id, currentActor()))
}

// 未来: GET /api/v1/kb/docs
export async function fetchKbDocuments(spaceId?: string): Promise<KbDocument[]> {
  await delay()

  return readMock(service.listDocuments(database().db, currentActor(), spaceId))
}

// 未来: GET /api/v1/kb/docs/{id}
export async function fetchKbDocument(id: string): Promise<KbDocument | null> {
  await delay()

  return readMock(service.getDocument(database().db, id, currentActor()))
}

// 未来: GET /api/v1/kb/search
export async function searchKb(query: string): Promise<KbSearchResult[]> {
  await delay()

  return readMock(service.search(database().db, query, currentActor()))
}

// 未来: POST /api/v1/kb/docs
export async function createKbDocument(input: Pick<KbDocument, 'title' | 'content' | 'kind' | 'spaceId' | 'tags' | 'expiresOn'>): Promise<KbDocument> {
  await delay(); assertCan('create')

  const result = service.createDocument(database().db, input, currentActor())

  database().persist()

  return readMock(result)
}

// 未来: POST /api/v1/kb/docs/{id}/submit
export async function submitKbDocument(id: string): Promise<KbDocument> {
  await delay(); assertCan('update')

  const result = service.submitDocument(database().db, id, currentActor())

  database().persist()

  return readMock(result)
}

// 未来: POST /api/v1/kb/docs/{id}/versions
export async function createKbVersion(id: string, content: string): Promise<KbDocument> {
  await delay(); assertCan('update')

  const result = service.addVersion(database().db, id, content, currentActor())

  database().persist()

  return readMock(result)
}

// 未来: GET /api/v1/kb/reviews
export async function fetchKbReviews(): Promise<KbReviewItem[]> {
  await delay()

  return readMock(service.listReviews(database().db, currentActor()))
}

// 未来: POST /api/v1/kb/reviews/{id}/decide
export async function decideKbReview(id: string, decision: 'approve' | 'reject', reason = ''): Promise<KbReviewItem> {
  await delay(); assertCan('approve')

  const result = service.decideReview(database().db, id, decision, reason, currentActor())

  database().persist()

  return readMock(result)
}

// 未来: POST /api/v1/kb/qa/suggest
export async function suggestKbQa(ticketId: string): Promise<KbQaItem> {
  await delay(); assertCan('suggest')

  const result = service.suggestQa(database().db, ticketId, currentActor())

  database().persist()

  return readMock(result)
}

// 未来: GET /api/v1/kb/qa
export async function fetchKbQa(): Promise<KbQaItem[]> {
  await delay()

  return readMock(service.listQa(database().db, currentActor()))
}

// 未来: GET /api/v1/kb/expiring
export async function fetchKbExpiring(): Promise<KbExpiryItem[]> {
  await delay()

  return readMock(service.listExpiring(database().db, currentActor()))
}

// 未来: POST /api/v1/kb/index/rebuild
export async function rebuildKbIndex(): Promise<number> {
  await delay(); assertCan('update')

  const result = service.rebuildIndex(database().db, currentActor())

  database().persist()

  return readMock(result)
}

// 未来: GET /api/v1/audit/logs?category=kb_sensitive
export async function fetchKbAccessLogs(): Promise<KbAccessLog[]> {
  await delay()

  return readMock(service.listAccessLogs(database().db, currentActor()))
}

// 未来: PUT /api/v1/kb/spaces/{id}/acl
export async function setKbSpaceFinanceOnly(id: string, financeOnly: boolean): Promise<KbSpace | null> {
  await delay(); assertCan('update')

  const actor = currentActor(); const space = service.getSpace(database().db, id, { ...actor, role: 'admin' }); if (!space || actor.role !== 'admin')
    throw new Error('只有空间管理员可以修改权限'); space.financeOnly = financeOnly; space.updatedAt = actor.at; database().persist()

  return readMock(space)
}

// 未来: GET /api/v1/kb/personal/{employeeId}
export async function fetchEmployeeFiles(employeeId: string): Promise<EmployeeFile[]> {
  await delay()

  return readMock(service.listEmployeeFiles(database().db, employeeId, currentActor()))
}

// 未来: POST /api/v1/kb/personal/{employeeId}/files/{id}/download
export async function downloadEmployeeFile(employeeId: string, id: string): Promise<EmployeeFile> {
  await delay()

  const result = service.downloadEmployeeFile(database().db, id, employeeId, currentActor())

  database().persist()

  return readMock(result)
}

// 未来: GET /api/v1/onboarding/me
export async function fetchOnboarding(roleId: string): Promise<OnboardingChecklistItem[]> {
  await delay()

  return readMock(service.listOnboarding(database().db, roleId))
}

// 未来: PUT /api/v1/onboarding/checklists/{id}
export async function saveOnboarding(item: OnboardingChecklistItem): Promise<OnboardingChecklistItem> {
  await delay()

  const result = service.saveOnboardingItem(database().db, item, currentActor())

  database().persist()

  return readMock(result)
}

// 未来: POST /api/v1/onboarding/ask
export async function askOnboarding(question: string): Promise<OnboardingAnswer> {
  await delay()

  return readMock(service.askKnowledge(database().db, question, currentActor()))
}

// 未来: GET /api/v1/kb/docs/{id}/versions
export async function fetchKbVersions(id: string): Promise<KbVersion[]> {
  await delay()

  return readMock((service.getDocument(database().db, id, currentActor())?.versions ?? []))
}
