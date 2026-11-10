import { assertPermission, currentActor, database, delay, readMock } from '@/api/mock-client'
import { addSuggestionStep, listAgentTasks, listEvalCases, listEvalRuns, listKnowledgeDocuments, listPromptVersions, listRunSteps, listSecurityEvents, listUsageCalls, recordAgentRun } from '@/mocks/services/agent-module'
import { FlowError } from '@/mocks/services/errors'
import { useSessionStore } from '@/stores/session'
import type { AgentRunStep, AgentTask, EvalCase, EvalRun, KnowledgeDocument, PromptVersion, SecurityEvent, UsageCall } from '@/types/agent-module'
import type { AgentRun, CurrencyCode } from '@/types/domain'
import type { Actor, ApprovalEntity } from '@/types/entities'
import { requireActorPermission } from '@/utils/service-permissions'

const SESSION_CHANGED = '会话已变更，已放弃写入'

interface SuggestionDraft {
  title: string
  summary: string
  amount: string
  currency: CurrencyCode
  storeId: string | null
  targetType: string
  targetId: string
}

interface BoundInitiator {
  userId: string
  role: Actor['role']
  actor: Actor & { id: string }
}

function permissionDenied(permissionKey: string) {
  return new FlowError(`当前用户没有权限：${permissionKey}`)
}

/** 发起时拍下普通对象快照。延迟返回后只允许这个发起者落库。 */
function bindInitiator(permissionKey: string): BoundInitiator {
  const session = useSessionStore()

  if (!session.isLoggedIn || !session.userId || !session.role)
    throw permissionDenied(permissionKey)

  const live = currentActor()

  const actor: Actor & { id: string } = {
    userId: live.userId,
    id: live.userId,
    name: live.name,
    role: live.role,
    at: live.at,
  }

  if (!actor.userId || !actor.role)
    throw permissionDenied(permissionKey)

  requireActorPermission(actor, permissionKey)

  return { userId: actor.userId, role: actor.role, actor }
}

function assertInitiatorUnchanged(bound: BoundInitiator) {
  const session = useSessionStore()

  const sameIdentity = session.isLoggedIn
    && session.userId === bound.userId
    && session.role === bound.role
    && session.userId === bound.actor.userId

  // 身份变化不是权限不足：放弃写入，不用返回时的新身份落库。
  if (!sameIdentity)
    throw new FlowError(SESSION_CHANGED)
}

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
  const initiator = bindInitiator('agent_tool:read')

  await delay()
  assertInitiatorUnchanged(initiator)

  const run = recordAgentRun(database().db, { question, agentName }, initiator.actor)

  database().persist()

  return readMock(run)
}

// 未来: POST /api/v1/agent/runs/{id}/suggestion-step
export async function recordSuggestionStep(runId: string, approvalId: string) {
  const initiator = bindInitiator('agent_tool:write')

  await delay()
  assertInitiatorUnchanged(initiator)

  addSuggestionStep(database().db, runId, approvalId, initiator.actor)
  database().persist()
}

// 未来: POST /api/v1/approvals。只生成待审批建议，不审批、不写账。
export async function submitAgentSuggestion(input: SuggestionDraft): Promise<ApprovalEntity> {
  const initiator = bindInitiator('agent_suggestion:create')

  await delay()
  assertInitiatorUnchanged(initiator)

  return database().suggest(input, initiator.actor)
}
