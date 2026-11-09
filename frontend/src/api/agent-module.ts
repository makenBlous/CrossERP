import { assertCan, database, delay, readMock } from '@/api/mock-client'
import { addSuggestionStep, listAgentTasks, listEvalCases, listEvalRuns, listKnowledgeDocuments, listPromptVersions, listRunSteps, listSecurityEvents, listUsageCalls, recordAgentRun } from '@/mocks/services/agent-module'
import type { AgentRunStep, AgentTask, EvalCase, EvalRun, KnowledgeDocument, PromptVersion, SecurityEvent, UsageCall } from '@/types/agent-module'
import type { AgentRun } from '@/types/domain'

// 未来: GET /api/v1/agent/tasks
export async function fetchAgentTasks(): Promise<AgentTask[]> {
  await delay()

  return readMock(listAgentTasks(database().db))
}

// 未来: GET /api/v1/agent/tasks/{id}
export async function fetchAgentTask(id: string): Promise<AgentTask | null> {
  await delay()

  return readMock(listAgentTasks(database().db).find(row => row.id === id) ?? null)
}

// 未来: GET /api/v1/agent/knowledge/documents
export async function fetchKnowledgeDocuments(knowledgeBaseId?: string): Promise<KnowledgeDocument[]> {
  await delay()

  return readMock(listKnowledgeDocuments(database().db, knowledgeBaseId))
}

// 未来: GET /api/v1/agent/prompts
export async function fetchPromptVersions(): Promise<PromptVersion[]> {
  await delay()

  return readMock(listPromptVersions(database().db))
}

// 未来: GET /api/v1/agent/evals
export async function fetchEvalRuns(): Promise<EvalRun[]> {
  await delay()

  return readMock(listEvalRuns(database().db))
}

// 未来: GET /api/v1/agent/evals/{id}/cases
export async function fetchEvalCases(id: string): Promise<EvalCase[]> {
  await delay()

  return readMock(listEvalCases(database().db, id))
}

// 未来: GET /api/v1/agent/runs/{id}/steps
export async function fetchRunSteps(id: string): Promise<AgentRunStep[]> {
  await delay()

  return readMock(listRunSteps(database().db, id))
}

// 未来: GET /api/v1/agent/usage/calls
export async function fetchUsageCalls(): Promise<UsageCall[]> {
  await delay()

  return readMock(listUsageCalls(database().db))
}

// 未来: GET /api/v1/security/events
export async function fetchSecurityEvents(): Promise<SecurityEvent[]> {
  await delay()

  return readMock(listSecurityEvents(database().db))
}

// 未来: POST /api/v1/agent/runs
export async function recordAgentQuestion(question: string, agentName?: string): Promise<AgentRun> {
  await delay()

  const actor = assertCan('view')
  const run = recordAgentRun(database().db, { question, agentName }, actor)

  database().persist()

  return readMock(run)
}

// 未来: POST /api/v1/agent/runs/{id}/suggestion-step
export async function recordSuggestionStep(runId: string, approvalId: string) {
  await delay()

  const actor = assertCan('suggest')

  addSuggestionStep(database().db, runId, approvalId, actor)
  database().persist()
}
