import type { Actor, AgentRunEntity, AuditEvent, MockDatabase } from '@/types/entities'
import type { AgentRunStep, AgentTask, EvalCase, EvalRun, KnowledgeDocument, PromptVersion, SecurityEvent, UsageCall } from '@/types/agent-module'
import { nextId } from '@/mocks/services/ids'
import { writeAudit } from '@/mocks/services/audit'

interface AgentCollections {
  agentTasks: AgentTask[]
  knowledgeDocuments: KnowledgeDocument[]
  promptVersions: PromptVersion[]
  evalRuns: EvalRun[]
  evalCases: EvalCase[]
  agentRunSteps: AgentRunStep[]
  usageCalls: UsageCall[]
  securityEvents: SecurityEvent[]
}

function collections(db: MockDatabase): AgentCollections {
  const value = db as MockDatabase & Partial<AgentCollections>

  value.agentTasks ??= []
  value.knowledgeDocuments ??= []
  value.promptVersions ??= []
  value.evalRuns ??= []
  value.evalCases ??= []
  value.agentRunSteps ??= []
  value.usageCalls ??= []
  value.securityEvents ??= []

  return value as MockDatabase & AgentCollections
}

export function listAgentTasks(db: MockDatabase) {
  return collections(db).agentTasks
}
export function listKnowledgeDocuments(db: MockDatabase, knowledgeBaseId?: string) {
  const rows = collections(db).knowledgeDocuments

  return knowledgeBaseId ? rows.filter(row => row.knowledgeBaseId === knowledgeBaseId) : rows
}
export function listPromptVersions(db: MockDatabase) {
  return collections(db).promptVersions
}
export function listEvalRuns(db: MockDatabase) {
  return collections(db).evalRuns
}
export function listEvalCases(db: MockDatabase, runId: string) {
  return collections(db).evalCases.filter(row => row.runId === runId)
}
export function listRunSteps(db: MockDatabase, runId: string) {
  return collections(db).agentRunSteps.filter(row => row.runId === runId)
}
export function listUsageCalls(db: MockDatabase) {
  return collections(db).usageCalls
}
export function listSecurityEvents(db: MockDatabase) {
  return collections(db).securityEvents
}

export function recordAgentRun(db: MockDatabase, input: { question: string; agentName?: string; runId?: string }, actor: Actor): AgentRunEntity {
  const run: AgentRunEntity = {
    id: input.runId ?? nextId(db, 'run'),
    agentName: input.agentName ?? '对账解释员',
    startedAt: actor.at,
    durationMs: 2860,
    tokens: 1240,
    costUsd: 0.011,
    status: 'succeeded',
    question: input.question,
  }

  db.agentRuns.unshift(run)

  const ext = collections(db)

  ext.agentRunSteps.unshift(
    { id: nextId(db, 'step'), runId: run.id, kind: 'plan', title: '制定只读查询计划', detail: '识别问题并选择只读工具', at: actor.at.slice(11, 19), redacted: false },
    { id: nextId(db, 'step'), runId: run.id, kind: 'tool', title: '只读工具调用', detail: '结果来自 CrossERP 已存储快照，入参已脱敏', at: actor.at.slice(11, 19), input: '{"record":"[REDACTED]"}', output: '{"source":"stored_snapshot"}', redacted: true },
    { id: nextId(db, 'step'), runId: run.id, kind: 'answer', title: '生成回答', detail: '回答明确金额来源和审批边界', at: actor.at.slice(11, 19), redacted: false },
  )
  ext.usageCalls.unshift({ id: nextId(db, 'call'), runId: run.id, model: 'placeholder-model-A', createdAt: actor.at, inputTokens: 720, outputTokens: 520, totalTokens: 1240, costUsd: run.costUsd, redactionFlags: ['record_id'], injectionCheck: 'passed' })
  writeAudit(db, actor, 'agent.run', 'agent_run', run.id, `智能体运行 ${run.id} 已记录。工具调用为只读。`)

  return run
}

export function addSuggestionStep(db: MockDatabase, runId: string, approvalId: string, actor: Actor) {
  collections(db).agentRunSteps.push({ id: nextId(db, 'step'), runId, kind: 'suggestion', title: '生成待审批建议', detail: `建议 ${approvalId} 已进入审批队列，未写入业务数据`, at: actor.at.slice(11, 19), output: '{"approval":"pending"}', redacted: true })
}

export function addSecurityEvent(db: MockDatabase, event: SecurityEvent) {
  collections(db).securityEvents.unshift(event)
}

export function auditEvents(db: MockDatabase): AuditEvent[] {
  return [...db.audit].sort((a, b) => b.at.localeCompare(a.at))
}
