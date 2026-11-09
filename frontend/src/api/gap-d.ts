import { currentActor, database, delay } from '@/api/mock-client'
import { approveGapDLeave, approveGapDPayroll, calculateGapDPayroll, checkoutGapDAsset, configureGapDTool, editGapDContract, gapDAutonomyPolicies, gapDPayrollRules, gapDTools, getGapDPayrollRun, importGapDMcpTool, ingestGapDInbox, listGapDAudit, listGapDRecords, publishGapDPayslips, registerGapDImport, registerGapDMcpServer, returnGapDAsset, reviewGapDPayroll, saveGapDDeduction, saveGapDPayrollRule, saveGapDRecord, saveGapDTool, submitGapDLeave, testGapDTool, toggleGapDTool, transitionGapDEmployeeStatus, updateGapDAiMode, updateGapDAutonomy } from '@/mocks/services/gap-d'
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

// 未来: PATCH /api/v1/agent/tools/{id}
export async function setGapDToolEnabled(id: string, enabled: boolean): Promise<GapDTool> {
  await delay()

  const result = toggleGapDTool(id, enabled, currentActor())

  database().persist()

  return result
}

export async function configureGapDToolSettings(id: string, input: Parameters<typeof configureGapDTool>[1]) {
  await delay()

  const result = configureGapDTool(id, input, currentActor())

  database().persist()

  return result
}

export async function testGapDToolCall(id: string) {
  await delay()

  const result = testGapDTool(id, currentActor())

  database().persist()

  return result
}

// 未来: POST /api/v1/agent/inbox
export async function uploadGapDInbox(fileName: string): Promise<GapDRecord> {
  await delay()

  const result = ingestGapDInbox(fileName, currentActor())

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

export async function registerGapDMcp(input: Parameters<typeof registerGapDMcpServer>[0]) {
  await delay()

  const result = registerGapDMcpServer(input, currentActor())

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

export async function saveGapDOperation(pageId: GapDPageId, input: { title: string; detail?: string }) {
  await delay()

  const result = saveGapDRecord(pageId, input, currentActor())

  database().persist()

  return result
}

export async function transitionEmployeeStatus(employeeId: string, status: Parameters<typeof transitionGapDEmployeeStatus>[1]) {
  await delay()

  const result = transitionGapDEmployeeStatus(employeeId, status, currentActor())

  database().persist()

  return result
}

export async function editContract(contractId: string, input: Parameters<typeof editGapDContract>[1]) {
  await delay()

  const result = editGapDContract(contractId, input, currentActor())

  database().persist()

  return result
}

export async function checkoutAsset(assetId: string, employeeId: string) {
  await delay()

  const result = checkoutGapDAsset(assetId, employeeId, currentActor())

  database().persist()

  return result
}

export async function returnAsset(assetId: string) {
  await delay()

  const result = returnGapDAsset(assetId, currentActor())

  database().persist()

  return result
}

export async function submitLeave(input: Parameters<typeof submitGapDLeave>[0]) {
  await delay()

  const result = submitGapDLeave(input, currentActor())

  database().persist()

  return result
}

export async function approveLeave(id: string) {
  await delay()

  const result = approveGapDLeave(id, currentActor())

  database().persist()

  return result
}

export async function registerMockImport(kind: Parameters<typeof registerGapDImport>[0], fileName: string, rowCount: number) {
  await delay()

  const result = registerGapDImport(kind, fileName, rowCount, currentActor())

  database().persist()

  return result
}

export async function savePayrollRule(input: Parameters<typeof saveGapDPayrollRule>[0]) {
  await delay()

  const result = saveGapDPayrollRule(input, currentActor())

  database().persist()

  return result
}

export async function saveDeduction(input: Parameters<typeof saveGapDDeduction>[0]) {
  await delay()

  const result = saveGapDDeduction(input, currentActor())

  database().persist()

  return result
}

export async function reviewPayroll(runId: string, reason: string) {
  await delay()

  const result = reviewGapDPayroll(runId, reason, currentActor())

  database().persist()

  return result
}

export async function approvePayroll(runId: string) {
  await delay()

  const result = approveGapDPayroll(runId, currentActor())

  database().persist()

  return result
}

export async function publishPayslips(runId: string) {
  await delay()

  const result = publishGapDPayslips(runId, currentActor())

  database().persist()

  return result
}
