import { currentActor, database, delay } from '@/api/mock-client'
import { calculateGapDPayroll, gapDAutonomyPolicies, gapDPayrollRules, gapDTools, getGapDPayrollRun, importGapDMcpTool, listGapDAudit, listGapDRecords, saveGapDTool, updateGapDAiMode, updateGapDAutonomy } from '@/mocks/services/gap-d'
import type { AgentAutonomyLevel } from '@/types/foundation'
import type { GapDAiState, GapDAuditEvent, GapDPageId, GapDPayrollRun, GapDRecord, GapDTool } from '@/types/gap-d'

// 未来: GET /api/v1/gap-d/pages/{pageId}
export async function fetchGapDRecords(pageId: GapDPageId): Promise<GapDRecord[]> {
  await delay()

  return listGapDRecords(pageId, currentActor())
}

// 未来: GET /api/v1/agent/autonomy-policies
export async function fetchGapDAutonomyPolicies() {
  await delay()

  return structuredClone(gapDAutonomyPolicies)
}

// 未来: PATCH /api/v1/agent/autonomy-policies/{id}
export async function saveGapDAutonomy(id: string, level: AgentAutonomyLevel) {
  await delay()

  const result = updateGapDAutonomy(id, level, currentActor())

  database().persist()

  return result
}

// 未来: POST /api/v1/agent/mode
export async function setGapDAiMode(mode: GapDAiState['mode'], reason: string): Promise<GapDAiState> {
  await delay()

  const result = updateGapDAiMode(mode, reason, currentActor())

  database().persist()

  return result
}

// 未来: GET /api/v1/agent/tools
export async function fetchGapDTools(): Promise<GapDTool[]> {
  await delay()

  return structuredClone(gapDTools)
}

// 未来: POST /api/v1/agent/tools
export async function createGapDTool(input: Partial<GapDTool>): Promise<GapDTool> {
  await delay()

  const result = saveGapDTool(input, currentActor())

  database().persist()

  return result
}

// 未来: POST /api/v1/agent/mcp-servers/{id}/import
export async function importGapDMcp(serverId: string) {
  await delay()

  const result = importGapDMcpTool(serverId, currentActor())

  database().persist()

  return result
}

// 未来: GET /api/v1/hr/payroll-rules
export async function fetchGapDPayrollRules() {
  await delay()

  return structuredClone(gapDPayrollRules)
}

// 未来: POST /api/v1/hr/payroll-runs/calculate
export async function calculateGapDPayrollRun(period: string): Promise<GapDPayrollRun> {
  await delay()

  const result = calculateGapDPayroll(period, currentActor())

  database().persist()

  return result
}

// 未来: GET /api/v1/hr/payroll-runs/{id}
export async function fetchGapDPayrollRun(id: string): Promise<GapDPayrollRun | null> {
  await delay()

  return getGapDPayrollRun(id, currentActor())
}

// 未来: GET /api/v1/audit?module=agent/hr/office
export async function fetchGapDAudit(): Promise<GapDAuditEvent[]> {
  await delay()

  return structuredClone(listGapDAudit())
}
