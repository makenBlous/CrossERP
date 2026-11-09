import { delay } from '@/api/mock-client'
import * as service from '@/mocks/services/gap-c'
import type { FieldAccess, GapCAccessReview, GapCAgentTrace, GapCAlert, GapCApprovalRow, GapCApprovalRule, GapCArchiveRun, GapCAuditRow, GapCDataScope, GapCFieldPolicy, GapCMatrixCell, GapCNotification, GapCPermissionChange, GapCReport, GapCReportBuilder, GapCReportResult, GapCRetention, GapCRoleCopyInput, GapCRoleView, GapCSodRule, GapCSubscription, GapCTemporaryGrant } from '@/types/gap-c'

// 未来: GET /api/v1/approvals?scope=all|agent|cc
export async function fetchGapCApprovals(mode: 'all' | 'agent' | 'cc' = 'all'): Promise<GapCApprovalRow[]> {
  await delay()

  return service.listGapCApprovals(mode)
}

// 未来: POST /api/v1/approvals/{id}/decide
export async function decideGapCApproval(id: string, status: 'approved' | 'rejected'): Promise<GapCApprovalRow> {
  await delay()

  return service.decideGapCApproval(id, status)
}

// 未来: GET /api/v1/workflow/rules
export async function fetchGapCApprovalRules(): Promise<GapCApprovalRule[]> {
  await delay()

  return service.listGapCApprovalRules()
}

// 未来: PUT /api/v1/workflow/rules/{id}
export async function saveGapCApprovalRule(rule: GapCApprovalRule): Promise<GapCApprovalRule> {
  await delay()

  return service.saveGapCApprovalRule(rule)
}

// 未来: GET /api/v1/notify/messages
export async function fetchGapCNotifications(): Promise<GapCNotification[]> {
  await delay()

  return service.listGapCNotifications()
}

// 未来: POST /api/v1/notify/messages/{id}/read
export async function markGapCNotificationRead(id: string): Promise<GapCNotification | undefined> {
  await delay()

  return service.markGapCNotificationRead(id)
}

// 未来: GET /api/v1/notify/subscriptions
export async function fetchGapCSubscriptions(): Promise<GapCSubscription[]> {
  await delay()

  return service.listGapCSubscriptions()
}

// 未来: PUT /api/v1/notify/subscriptions
export async function saveGapCSubscriptions(items: GapCSubscription[]): Promise<GapCSubscription[]> {
  await delay()

  return service.saveGapCSubscriptions(items)
}

// 未来: GET /api/v1/reports
export async function fetchGapCReports(): Promise<GapCReport[]> {
  await delay()

  return service.listGapCReports()
}

// 未来: POST /api/v1/reports/{id}/run
export async function runGapCReport(id: string, period: string): Promise<GapCReportResult> {
  await delay()

  return service.runGapCReport(id, period)
}

// 未来: POST /api/v1/reports
export async function createGapCReport(input: { name: string; description: string; permissionKey: string; builder: GapCReportBuilder }): Promise<GapCReport> {
  await delay()

  return service.saveGapCReport(input)
}

// 未来: GET /api/v1/audit/logs?actor_type=agent
export async function fetchGapCAudit(): Promise<GapCAuditRow[]> {
  await delay()

  return service.listGapCAudit()
}

// 未来: GET /api/v1/audit/agent-trace/{suggestion_id}
export async function fetchGapCAgentTrace(id: string): Promise<GapCAgentTrace> {
  await delay()

  return service.getGapCAgentTrace(id)
}

// 未来: GET /api/v1/audit/alerts
export async function fetchGapCAlerts(): Promise<GapCAlert[]> {
  await delay()

  return service.listGapCAlerts()
}

// 未来: POST /api/v1/audit/alerts/{id}/resolve
export async function resolveGapCAlert(id: string): Promise<GapCAlert | undefined> {
  await delay()

  return service.resolveGapCAlert(id)
}

// 未来: GET /api/v1/audit/retention
export async function fetchGapCRetention(): Promise<GapCRetention> {
  await delay()

  return service.getGapCRetention()
}

// 未来: PUT /api/v1/audit/retention
export async function saveGapCRetention(next: GapCRetention): Promise<GapCRetention> {
  await delay()

  return service.saveGapCRetention(next)
}

// 未来: POST /api/v1/audit/retention/archive
export async function runGapCArchive(): Promise<GapCArchiveRun> {
  await delay()

  return service.runGapCArchive()
}

// 未来: GET /api/v1/audit/retention/archive-runs
export async function fetchGapCArchiveRuns(): Promise<GapCArchiveRun[]> {
  await delay()

  return service.listGapCArchiveRuns()
}

// 未来: GET /api/v1/admin/field-policies
export async function fetchGapCFieldPolicies(): Promise<GapCFieldPolicy[]> {
  await delay()

  return service.listGapCFieldPolicies()
}

// 未来: PUT /api/v1/admin/field-policies/{id}
export async function saveGapCFieldPolicy(id: string, access: FieldAccess): Promise<GapCFieldPolicy> {
  await delay()

  return service.saveGapCFieldPolicy(id, access)
}

// 未来: GET /api/v1/admin/data-scopes
export async function fetchGapCDataScopes(): Promise<GapCDataScope[]> {
  await delay()

  return service.listGapCDataScopes()
}

// 未来: PUT /api/v1/admin/data-scopes/{id}
export async function saveGapCDataScope(id: string, scope: GapCDataScope['scope']): Promise<GapCDataScope> {
  await delay()

  return service.saveGapCDataScope(id, scope)
}

// 未来: GET /api/v1/admin/temp-grants
export async function fetchGapCTemporaryGrants(): Promise<GapCTemporaryGrant[]> {
  await delay()

  return service.listGapCTemporaryGrants().map(item => ({ ...item, status: item.status as GapCTemporaryGrant['status'] }))
}

// 未来: POST /api/v1/admin/temp-grants
export async function createGapCTemporaryGrant(input: Omit<GapCTemporaryGrant, 'id' | 'status'>): Promise<GapCTemporaryGrant> {
  await delay()

  return service.saveGapCTemporaryGrant(input)
}

// 未来: GET /api/v1/admin/access-reviews
export async function fetchGapCAccessReviews(): Promise<GapCAccessReview[]> {
  await delay()

  return service.listGapCAccessReviews()
}

// 未来: POST /api/v1/admin/access-reviews/{id}/confirm
export async function confirmGapCAccessReview(id: string): Promise<GapCAccessReview> {
  await delay()

  return service.confirmGapCAccessReview(id)
}

// 未来: GET /api/v1/admin/roles
export async function fetchGapCRoles(): Promise<GapCRoleView[]> {
  await delay()

  return service.listGapCRoles()
}

// 未来: GET /api/v1/admin/roles/{id}
export async function fetchGapCRole(id: string): Promise<GapCRoleView> {
  await delay()

  return service.getGapCRole(id)
}

// 未来: POST /api/v1/admin/roles/{id}/copy
export async function copyGapCRole(input: GapCRoleCopyInput): Promise<GapCRoleView> {
  await delay()

  return service.copyGapCRole(input)
}

// 未来: GET /api/v1/admin/permission-matrix
export async function fetchGapCMatrix(): Promise<GapCMatrixCell[]> {
  await delay()

  return service.listGapCMatrix()
}

// 未来: PUT /api/v1/admin/permission-matrix
export async function saveGapCMatrix(cells: GapCMatrixCell[], confirmer?: string): Promise<GapCMatrixCell[]> {
  await delay()

  return service.saveGapCMatrix(cells, confirmer)
}

// 未来: GET /api/v1/admin/users/{id}/effective-permissions
export async function fetchGapCEffectivePermissions(id?: string) {
  await delay()

  return service.listGapCEffective(id)
}

// 未来: GET /api/v1/audit/logs?category=permission
export async function fetchGapCPermissionChanges(): Promise<GapCPermissionChange[]> {
  await delay()

  return service.listGapCPermissionChanges()
}

// 未来: GET /api/v1/admin/sod-rules
export async function fetchGapCSodRules(): Promise<GapCSodRule[]> {
  await delay()

  return service.listGapCSodRules()
}

// 未来: PUT /api/v1/admin/sod-rules/{id}
export async function saveGapCSodRule(id: string, enabled: boolean): Promise<GapCSodRule> {
  await delay()

  return service.saveGapCSodRule(id, enabled)
}
