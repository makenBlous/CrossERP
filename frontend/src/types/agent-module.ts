import type { Role } from '@/types/domain'

export interface AgentTask {
  id: string
  name: string
  agentId: string
  schedule: string
  status: 'active' | 'paused'
  nextRun: string
  steps: string[]
  lastRunId: string | null
}

export interface KnowledgeDocument {
  id: string
  knowledgeBaseId: string
  name: string
  format: 'PDF' | 'Markdown' | 'DOCX'
  chunks: number
  status: 'indexed' | 'processing' | 'disabled'
  updatedAt: string
}

export interface PromptVersion {
  id: string
  version: string
  name: string
  hash: string
  createdAt: string
  author: string
  active: boolean
  content: string
}

export interface EvalRun {
  id: string
  name: string
  model: string
  createdAt: string
  passRate: number
  passed: number
  total: number
  baseline: number
  status: 'passed' | 'warning' | 'running'
}

export interface EvalCase {
  id: string
  runId: string
  question: string
  expected: string
  actual: string
  passed: boolean
  citation: string
}

export interface AgentRunStep {
  id: string
  runId: string
  kind: 'plan' | 'tool' | 'suggestion' | 'answer'
  title: string
  detail: string
  at: string
  input?: string
  output?: string
  redacted?: boolean
}

export interface UsageCall {
  id: string
  runId: string
  model: string
  createdAt: string
  inputTokens: number
  outputTokens: number
  totalTokens: number
  costUsd: number
  redactionFlags: string[]
  injectionCheck: 'passed' | 'blocked' | 'review'
}

export interface SecurityEvent {
  id: string
  at: string
  actor: string
  actorRole: Role
  event: 'login_success' | 'login_failure' | 'lockout' | 'token_created' | 'role_changed' | 'denied_access'
  summary: string
  ip: string
}

export interface AuditChainEntry {
  index: number
  eventId: string
  prevHash: string
  hash: string
}
