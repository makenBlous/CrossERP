import type { Role } from '@/types/domain'

export type ApprovalDocStatus = 0 | 1 | 2
export type ApprovalBusinessStatus = 'draft' | 'pending' | 'approved' | 'rejected' | 'cancelled'
export type ApprovalAction = 'approve' | 'reject' | 'submit' | 'cancel'

export interface ApprovalRule {
  id: string
  level: number
  approverType: 'role' | 'user' | 'department_manager'
  approverRef: string
  minAmount?: number
  maxAmount?: number
  currency?: string
  imApprovalEnabled: boolean
  imApprovalMaxAmount?: number
  imChannelIds: string[]
}

export interface ApprovalTypeDefinition {
  id: string
  code: string
  nameZh: string
  nameEn: string
  docType: string
  docStatus: ApprovalDocStatus
  businessStatus: ApprovalBusinessStatus
  rules: ApprovalRule[]
  defaultImApprovalEnabled: boolean
  imAmountThreshold?: number
}

export type DocumentOrigin = 'human' | 'agent' | 'system' | 'import'

export interface DocumentLink {
  id: string
  fromDocType: string
  fromDocId: string
  toDocType: string
  toDocId: string
  relation: 'source' | 'derived' | 'related' | 'approval'
  label: string
}

export type AgentAutonomyLevel = 'L0' | 'L1' | 'L2' | 'L3'
export type AgentSideEffect = 'none' | 'propose' | 'execute_l3'

export interface AgentSuggestion {
  id: string
  title: string
  summary: string
  origin: DocumentOrigin
  agentSuggestionId: string
  onBehalfOfUserId: string
  level: AgentAutonomyLevel
  confidence: 'high' | 'medium' | 'low'
  evidence: Array<{ label: string; href?: string; recordId?: string }>
  status: 'open' | 'accepted' | 'modified' | 'rejected' | 'expired'
  expiresAt: string
  docType?: string
  docId?: string
}

export interface AgentAutonomyPolicy {
  id: string
  moduleCode: string
  action: string
  roleId: string
  level: AgentAutonomyLevel
  sideEffect: AgentSideEffect
  dailyLimit: number
  usedToday: number
  whitelist: boolean
  hardMaxLevel: AgentAutonomyLevel
  reason: string
}

export type AiMode = 'normal' | 'degraded' | 'off'

export interface AiModeState {
  mode: AiMode
  changedAt: string
  changedBy: string
  reason: string
}

export interface Department {
  id: string
  code: string
  name: string
  parentId: string | null
  managerUserId: string | null
  active: boolean
}

export type PermissionKind = 'menu' | 'action' | 'field'
export type DataScopeRuleType = 'all' | 'store' | 'department' | 'self' | 'owner' | 'warehouse' | 'amount'
export type PermissionEffect = 'allow' | 'deny'

export interface PermissionPoint {
  key: string
  labelZh: string
  labelEn: string
  module: string
  kind: PermissionKind
  sensitive?: boolean
  dataScopeRuleTypes?: DataScopeRuleType[]
  erpnextRef?: string
  odooRef?: string
}

export interface RolePermission {
  permissionKey: string
  effect: PermissionEffect
  dataScopes?: DataScopeRuleType[]
  source?: string
}

export interface RoleTemplate {
  id: string
  nameZh: string
  nameEn: string
  parentIds: string[]
  permissions: RolePermission[]
  defaultDataScopes: DataScopeRuleType[]
  fieldRestrictions: Record<string, 'hidden' | 'masked' | 'readonly' | 'visible'>
  legacyRole?: Role
  erpnextRefs: string[]
  odooRefs: string[]
}

export interface UserPermissionOverride {
  id: string
  userId: string
  permissionKey: string
  effect: PermissionEffect
  reason: string
  startsAt?: string
  expiresAt?: string
}

export interface TemporaryGrant extends UserPermissionOverride {
  grantType: 'temporary'
}

export interface PermissionSubject {
  userId: string
  roleIds: string[]
  overrides?: UserPermissionOverride[]
  temporaryGrants?: TemporaryGrant[]
}

export interface EffectivePermission {
  permissionKey: string
  allowed: boolean
  sources: string[]
  deniedBy: string[]
  dataScopes: DataScopeRuleType[]
}

export interface AgentCardEvidence {
  label: string
  href?: string
  recordId?: string
}

export interface ChannelCapabilities {
  sendMessage: boolean
  approvalCard: boolean
  verifyCallback: boolean
  bindIdentity: boolean
}

export interface ChannelMessage {
  subject: string
  body: string
  recipient: string
}

export interface ApprovalCardPayload {
  approvalId: string
  title: string
  summary: string
  amount?: number
  currency?: string
  contentHash: string
  approveUrl?: string
}

export interface ChannelPlugin {
  id: string
  nameZh: string
  nameEn: string
  capabilities: ChannelCapabilities
  sendMessage(message: ChannelMessage): Promise<{ ok: boolean; messageId: string }>
  sendApprovalCard(card: ApprovalCardPayload): Promise<{ ok: boolean; messageId: string }>
  verifyCallback(payload: string, signature: string): boolean
  bindIdentity(externalAccount: string, userId: string): Promise<{ ok: boolean; bindingId: string }>
}

export interface ModuleSwitch {
  id: string
  nameZh: string
  nameEn: string
  enabled: boolean
  defaultPhase: 'now' | 'v1' | 'later'
}

