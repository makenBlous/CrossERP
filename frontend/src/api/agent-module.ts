import { assertPermission, database, delay, readMock } from '@/api/mock-client'
import { addSuggestionStep, listAgentTasks, listEvalCases, listEvalRuns, listKnowledgeDocuments, listPromptVersions, listRunSteps, listSecurityEvents, listUsageCalls, recordAgentRun } from '@/mocks/services/agent-module'
import type { AgentRunStep, AgentTask, EvalCase, EvalRun, KnowledgeDocument, PromptVersion, SecurityEvent, UsageCall } from '@/types/agent-module'
import type { AgentRun } from '@/types/domain'

// 未来: GET /api/v1/agent/tasks
export async function fetchAgentTasks(): Promise<AgentTask[]> {
  await delay()
  assertPermission('agent_tool:read')

  return readMock(listAgentTasks(database().db))
}

// 未来: GET /api/v1/agent/tasks/{id}
export async function fetchAgentTask(id: string): Promise<AgentTask | null> {
  await delay()
  assertPermission('agent_tool:read')

  return readMock(listAgentTasks(database().db).find(row => row.id === id) ?? null)
}

// 未来: GET /api/v1/agent/knowledge/documents
export async function fetchKnowledgeDocuments(knowledgeBaseId?: string): Promise<KnowledgeDocument[]> {
  await delay()
  assertPermission('document:read')

  return readMock(listKnowledgeDocuments(database().db, knowledgeBaseId))
}

// 未来: GET /api/v1/agent/prompts
export async function fetchPromptVersions(): Promise<PromptVersion[]> {
  await delay()
  assertPermission('agent_tool:read')

  return readMock(listPromptVersions(database().db))
}

// 未来: GET /api/v1/agent/evals
export async function fetchEvalRuns(): Promise<EvalRun[]> {
  await delay()
  assertPermission('agent_tool:read')

  return readMock(listEvalRuns(database().db))
}

// 未来: GET /api/v1/agent/evals/{id}/cases
export async function fetchEvalCases(id: string): Promise<EvalCase[]> {
  await delay()
  assertPermission('agent_tool:read')

  return readMock(listEvalCases(database().db, id))
}

// 未来: GET /api/v1/agent/runs/{id}/steps
export async function fetchRunSteps(id: string): Promise<AgentRunStep[]> {
  await delay()
  assertPermission('agent_tool:read')

  return readMock(listRunSteps(database().db, id))
}

// 未来: GET /api/v1/agent/usage/calls
export async function fetchUsageCalls(): Promise<UsageCall[]> {
  await delay()
  assertPermission('agent_tool:read')

  return readMock(listUsageCalls(database().db))
}

// 未来: GET /api/v1/security/events
export async function fetchSecurityEvents(): Promise<SecurityEvent[]> {
  await delay()
  assertPermission('audit_log:read')

  return readMock(listSecurityEvents(database().db))
}

// 未来: POST /api/v1/agent/runs
export async function recordAgentQuestion(question: string, agentName?: string): Promise<AgentRun> {
  await delay()

  const actor = assertPermission('agent_tool:read')
  const run = recordAgentRun(database().db, { question, agentName }, actor)

  database().persist()

  return readMock(run)
}

// 未来: POST /api/v1/agent/runs/{id}/suggestion-step
export async function recordSuggestionStep(runId: string, approvalId: string) {
  await delay()

  const actor = assertPermission('agent_tool:write')

  addSuggestionStep(database().db, runId, approvalId, actor)
  database().persist()
}
