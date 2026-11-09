import type { AgentAutonomyLevel, AiMode } from '@/types/foundation'

export type GapDPageId =
  | 'G04'
  | 'G18' | 'G19' | 'G20' | 'G21' | 'G22' | 'G23' | 'G24' | 'G25' | 'G26'
  | 'HR01' | 'HR02' | 'HR03' | 'HR04' | 'HR05' | 'HR06' | 'HR07' | 'HR08' | 'HR09' | 'HR10' | 'HR11' | 'HR12'
  | 'AM01' | 'AM02' | 'AM03' | 'AM04' | 'AM05'

export interface GapDRecord {
  id: string
  title: string
  status: string
  owner?: string
  department?: string
  amount?: number
  currency?: string
  detail?: string
  updatedAt: string
  [key: string]: unknown
}

export interface GapDTool {
  id: string
  name: string
  kind: 'erp' | 'web' | 'mcp' | 'http'
  sideEffect: 'none' | 'propose' | 'execute_l3'
  enabled: boolean
  readOnly: boolean
  secretConfigured: boolean
  frequencyLimit: number
  autonomyLevel: AgentAutonomyLevel
  roles: string[]
  endpoint?: string
  lastCallAt?: string
}

export interface GapDMcpServer {
  id: string
  name: string
  transport: 'stdio' | 'http'
  endpoint: string
  status: 'connected' | 'error' | 'disabled'
  discoveredTools: string[]
  imported: boolean
}

export interface GapDPayrollRule {
  id: string
  city: string
  effectiveFrom: string
  pensionRate: number
  medicalRate: number
  unemploymentRate: number
  housingFundRate: number
  baseMinCents: number
  baseMaxCents: number
  verified: boolean
}

export interface GapDDeduction {
  id: string
  employeeId: string
  employeeName: string
  category: string
  monthlyCents: number
  effectiveFrom: string
  effectiveTo?: string
  status: 'active' | 'pending'
}

export interface GapDEmployee {
  id: string
  userId: string
  name: string
  department: string
  title: string
  email: string
  status: '在职' | '试用' | '离职'
  manager?: string
  leaveBalanceDays: number
  salaryCents?: number
  idNumber?: string
}

export interface GapDPayslip {
  id: string
  employeeId: string
  employeeUserId: string
  employeeName: string
  period: string
  grossCents: number
  socialPersonalCents: number
  housingFundPersonalCents: number
  taxableCumulativeCents: number
  taxCents: number
  netCents: number
  ruleVersion: string
  status: '待复核' | '待审批' | '已出凭证'
}

export interface GapDPayrollRun {
  id: string
  period: string
  status: '待计算' | '待复核' | '待审批' | '已出凭证'
  employeeCount: number
  payslips: GapDPayslip[]
  createdAt: string
}

export interface GapDAuditEvent {
  id: string
  action: string
  origin: 'human' | 'ai' | 'system'
  agentSuggestionId?: string
  actor: string
  at: string
  detail: string
}

export interface GapDAiState {
  mode: AiMode
  changedAt: string
  changedBy: string
  reason: string
}
