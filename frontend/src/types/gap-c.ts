import type { CurrencyCode } from '@/types/domain'
import type { DataScopeRuleType, EffectivePermission, PermissionEffect, RoleTemplate } from '@/types/foundation'

export type FieldAccess = 'hidden' | 'masked' | 'readonly' | 'visible'

export type GapCApprovalKind = 'expense' | 'leave' | 'purchase' | 'voucher' | 'agent'
export type GapCApprovalStatus = 'pending' | 'approved' | 'rejected' | 'cc'

export interface GapCApprovalRow {
  id: string
  kind: GapCApprovalKind
  typeLabel: string
  title: string
  submitter: string
  submitterId: string
  department: string
  shopId: string
  amount: number
  currency: CurrencyCode
  status: GapCApprovalStatus
  origin: 'human' | 'agent'
  agentSuggestionId?: string
  submittedAt: string
  summary: string
  approvalLevel: number
  nextApprover: string
}

export interface GapCApprovalRule {
  id: string
  type: string
  level: number
  minAmount: number
  maxAmount?: number
  approver: string
  department: string
  imEnabled: boolean
}

export interface GapCNotification {
  id: string
  title: string
  body: string
  category: 'approval' | 'budget' | 'agent' | 'system'
  read: boolean
  createdAt: string
  href?: string
}

export interface GapCSubscription {
  id: string
  event: string
  description: string
  inApp: boolean
  feishu: boolean
  wecom: boolean
  email: boolean
}

export interface GapCReport {
  id: string
  name: string
  description: string
  module: string
  lastRunAt: string
  permissionKey: string
  columns: string[]
  builder?: GapCReportBuilder
}

export interface GapCReportBuilder {
  dataSource: 'orders' | 'expenses' | 'employees' | 'audit'
  fields: string[]
  filters: Array<{ field: string; operator: 'equals' | 'contains' | 'gte' | 'lte'; value: string }>
}

export interface GapCReportResult {
  id: string
  reportId: string
  period: string
  rows: Array<Record<string, string | number>>
  generatedAt: string
  totals: Record<string, number>
}

export interface GapCAuditRow {
  id: string
  at: string
  actor: string
  actorType: 'human' | 'agent' | 'system'
  onBehalfOf?: string
  action: string
  objectType: string
  objectId: string
  reason: string
  approvalId?: string
  ipDevice: string
  agentSuggestionId?: string
}

export interface GapCAgentTrace {
  suggestionId: string
  question: string
  runId: string
  actor: string
  onBehalfOf: string
  level: string
  confidence: string
  steps: Array<{ at: string; title: string; detail: string; status: 'ok' | 'warning' | 'missing' }>
  outcome: string
}

export interface GapCAlert {
  id: string
  severity: 'high' | 'medium' | 'low'
  title: string
  detail: string
  createdAt: string
  resolved: boolean
  href?: string
}

export interface GapCRetention {
  businessYears: number
  aiYears: number
  archiveAfterDays: number
  lastArchiveAt: string
  immutable: boolean
}

export interface GapCArchiveRun {
  id: string
  policyId: string
  startedAt: string
  archivedCount: number
  status: 'simulated' | 'completed'
  note: string
}

export interface GapCFieldPolicy {
  id: string
  roleId: string
  roleName: string
  objectType: string
  fieldKey: string
  fieldLabel: string
  access: FieldAccess
  sensitive: boolean
}

export interface GapCDataScope {
  id: string
  roleId: string
  roleName: string
  objectType: string
  scope: DataScopeRuleType
  values: string[]
  description: string
}

export interface GapCTemporaryGrant {
  id: string
  userId: string
  userName: string
  permissionKey: string
  effect: PermissionEffect
  reason: string
  startsAt: string
  expiresAt: string
  status: 'active' | 'expired'
}

export interface GapCAccessReview {
  id: string
  userId: string
  userName: string
  reviewer: string
  dueAt: string
  permissionCount: number
  unusedCount: number
  status: 'pending' | 'confirmed' | 'revoked'
}

export interface GapCRoleView extends RoleTemplate {
  memberCount: number
  status: 'active' | 'paused'
  memberUserIds?: string[]
  dataScopeLabel?: string
  isCustom?: boolean
}

export interface GapCRoleCopyInput {
  sourceRoleId: string
  nameZh: string
  nameEn: string
  dataScopes: DataScopeRuleType[]
  memberUserIds: string[]
}

export type GapCMatrixEffect = 'allow' | 'inherit' | 'deny' | 'none'

export interface GapCMatrixCell {
  roleId: string
  permissionKey: string
  effect: GapCMatrixEffect
  sensitive: boolean
}

export interface GapCEffectiveRow extends EffectivePermission {
  labelZh: string
  module: string
  sensitive: boolean
}

export interface GapCPermissionChange {
  id: string
  at: string
  actor: string
  confirmer?: string
  target: string
  action: string
  before: string
  after: string
  sensitive: boolean
}

export interface GapCSodRule {
  id: string
  firstAction: string
  secondAction: string
  objectType: string
  enabled: boolean
  reason: string
}
