import { assertPermission, database, delay, readMock } from '@/api/mock-client'
import { writeAudit } from '@/mocks/services/audit'
import { auditEvents } from '@/mocks/services/agent-module'
import { buildChain, verifyChain } from '@/mocks/services/audit-module'
import type { AuditChainEntry } from '@/types/agent-module'
import type { AuditEvent } from '@/types/entities'

// 未来: GET /api/v1/audit/events
export async function fetchAuditEvents(): Promise<AuditEvent[]> {
  await delay()
  assertPermission('audit_log:read')

  return readMock(auditEvents(database().db))
}

// 未来: GET /api/v1/audit/chain
export async function fetchAuditChain(): Promise<AuditChainEntry[]> {
  await delay()
  assertPermission('audit_log:read')

  return readMock(buildChain(database().db))
}

// 未来: POST /api/v1/audit/verify
export async function verifyAuditChain(tamperedIndex = -1) {
  await delay()
  assertPermission('audit_log:read')

  return readMock(verifyChain(database().db, tamperedIndex))
}

// 未来: POST /api/v1/audit/exports
export async function recordAuditExport(format: string, count: number) {
  await delay()

  const actor = assertPermission('audit_log:export')

  writeAudit(database().db, actor, 'audit.export', 'audit_package', `export-${Date.now()}`, `导出审计包（${format}，${count} 条记录）。`)
  database().persist()
}
