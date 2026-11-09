/* eslint-disable indent, max-statements-per-line */
import { currentActor, database } from '@/api/mock-client'
import { permissionCatalog, roleTemplates } from '@/config/permissions'
import { writeAudit } from '@/mocks/services/audit'
import type { Role } from '@/types/domain'
import type { DataScopeRuleType, PermissionSubject } from '@/types/foundation'
import { effectivePermission, fieldAccess, roleSubject } from '@/utils/permission-engine'
import { useSessionStore } from '@/stores/session'
import type {
  FieldAccess,
  GapCAccessReview,
  GapCAgentTrace,
  GapCAlert,
  GapCApprovalRow,
  GapCApprovalRule,
  GapCArchiveRun,
  GapCAuditRow,
  GapCDataScope,
  GapCEffectiveRow,
  GapCFieldPolicy,
  GapCMatrixCell,
  GapCNotification,
  GapCPermissionChange,
  GapCReport,
  GapCReportBuilder,
  GapCReportResult,
  GapCRetention,
  GapCRoleCopyInput,
  GapCRoleView,
  GapCSodRule,
  GapCSubscription,
  GapCTemporaryGrant,
} from '@/types/gap-c'

const actor = () => currentActor()
const subjectFor = (role: Role, userId = `demo-${role}`): PermissionSubject => roleSubject(role, userId)

const notifications: GapCNotification[] = [
  { id: 'msg-001', title: '预算使用达到 80%', body: '运营部 2026-11 费用预算已使用 82%，请关注后续报销。', category: 'budget', read: false, createdAt: '2026-11-10 09:12', href: '/finance/budgets' },
  { id: 'msg-002', title: '智能体建议待确认', body: '补货建议 sug-001 已进入统一审批中心。', category: 'agent', read: false, createdAt: '2026-11-10 08:40', href: '/approvals/agent-suggestions' },
  { id: 'msg-003', title: '凭证审批完成', body: '凭证 VCH-2026-011 已由财务主管批准。', category: 'approval', read: true, createdAt: '2026-11-09 17:20', href: '/finance/vouchers/vch-2026-011' },
]

let subscriptions: GapCSubscription[] = [
  { id: 'sub-budget', event: '预算达到 80%', description: '部门或科目预算使用率达到 80% 时提醒', inApp: true, feishu: true, wecom: false, email: true },
  { id: 'sub-approval', event: '审批待办', description: '有单据进入我的审批队列时提醒', inApp: true, feishu: true, wecom: true, email: false },
  { id: 'sub-agent', event: '智能体建议', description: '智能体创建建议或建议即将过期时提醒', inApp: true, feishu: false, wecom: false, email: true },
]

const approvals: GapCApprovalRow[] = [
  { id: 'gc-apr-001', kind: 'expense', typeLabel: '费用报销', title: '差旅住宿报销 · EXP-2026-081', submitter: '演示运营', submitterId: 'demo-operator', department: '运营部', shopId: 'shop-cn-01', amount: 2800, currency: 'CNY', status: 'pending', origin: 'human', submittedAt: '2026-11-10 09:10', summary: '上海客户拜访住宿，票据已上传。', approvalLevel: 1, nextApprover: '部门主管' },
  { id: 'gc-apr-002', kind: 'purchase', typeLabel: '采购申请', title: '补货采购 · PR-2026-014', submitter: '演示采购', submitterId: 'demo-purchaser', department: '供应链部', shopId: 'shop-us-01', amount: 8000, currency: 'CNY', status: 'pending', origin: 'human', submittedAt: '2026-11-10 08:55', summary: '安全库存不足，申请采购 120 件。', approvalLevel: 2, nextApprover: '财务主管' },
  { id: 'gc-apr-003', kind: 'agent', typeLabel: '智能体建议', title: '补货建议 · CN-1001', submitter: '演示运营', submitterId: 'demo-operator', department: '运营部', shopId: 'shop-cn-01', amount: 4200, currency: 'CNY', status: 'pending', origin: 'agent', agentSuggestionId: 'sug-001', submittedAt: '2026-11-10 08:40', summary: '智能体建议按安全库存补货，金额由系统已存字段提供。', approvalLevel: 1, nextApprover: '部门主管' },
  { id: 'gc-apr-005', kind: 'agent', typeLabel: '智能体建议', title: '部门主管自提交建议 · SELF-005', submitter: '演示部门主管', submitterId: 'demo-department-manager', department: '运营部', shopId: 'shop-cn-01', amount: 1200, currency: 'CNY', status: 'pending', origin: 'agent', submittedAt: '2026-11-10 08:35', summary: '用于演示职责分离：提交人不能批准自己的单据。', approvalLevel: 1, nextApprover: '部门主管' },
  { id: 'gc-apr-004', kind: 'leave', typeLabel: '请假申请', title: '年假 · LV-2026-033', submitter: '演示员工', submitterId: 'demo-employee', department: '运营部', shopId: 'shop-cn-01', amount: 0, currency: 'CNY', status: 'cc', origin: 'human', submittedAt: '2026-11-09 16:15', summary: '2026-11-18 至 2026-11-19 年假。', approvalLevel: 1, nextApprover: '部门主管' },
]

const approvalRules: GapCApprovalRule[] = [
  { id: 'rule-expense-1', type: '费用报销', level: 1, minAmount: 0, maxAmount: 3000, approver: '部门主管', department: '申请人所属部门', imEnabled: true },
  { id: 'rule-expense-2', type: '费用报销', level: 2, minAmount: 3000, approver: '财务主管', department: '财务部', imEnabled: true },
  { id: 'rule-purchase-1', type: '采购申请', level: 1, minAmount: 0, maxAmount: 5000, approver: '部门主管', department: '申请人所属部门', imEnabled: false },
  { id: 'rule-purchase-2', type: '采购申请', level: 2, minAmount: 5000, approver: '财务主管', department: '财务部', imEnabled: true },
]

const reports: GapCReport[] = [
  { id: 'rpt-budget', name: '预算执行明细', description: '按部门、科目和期间查看预算使用情况。', module: '财务', lastRunAt: '2026-11-10 09:05', permissionKey: 'report:read', columns: ['部门', '预算', '已使用', '使用率'] },
  { id: 'rpt-approval', name: '审批效率分析', description: '统计审批数量、金额和平均处理时长。', module: '协作', lastRunAt: '2026-11-09 18:30', permissionKey: 'report:read', columns: ['类型', '待审批', '已批准', '平均时长'] },
  { id: 'rpt-audit', name: '敏感操作清单', description: '筛选权限、导出和审批等敏感动作。', module: '审计', lastRunAt: '2026-11-09 17:45', permissionKey: 'audit_log:read', columns: ['动作', '操作者', '对象', '时间'] },
]

const aiAudit: GapCAuditRow[] = [
  { id: 'ai-aud-001', at: '2026-11-10 08:40', actor: '补货助手', actorType: 'agent', onBehalfOf: '演示运营', action: 'draft_replenishment', objectType: 'agent_suggestion', objectId: 'sug-001', reason: '安全库存低于阈值', approvalId: 'gc-apr-003', ipDevice: 'agent-runtime', agentSuggestionId: 'sug-001' },
  { id: 'ai-aud-002', at: '2026-11-09 15:20', actor: '审计助手', actorType: 'agent', onBehalfOf: '演示审计', action: 'read_report', objectType: 'report', objectId: 'rpt-budget', reason: '用户主动查询预算执行', ipDevice: 'agent-runtime' },
]

const traces: GapCAgentTrace[] = [{
  suggestionId: 'sug-001',
  question: '哪些 SKU 低于安全库存？',
  runId: 'run-001',
  actor: '补货助手',
  onBehalfOf: '演示运营',
  level: 'L2',
  confidence: 'high',
  steps: [
    { at: '08:39:40', title: '读取库存余额', detail: 'I02 / bal-001，按演示运营的数据范围过滤', status: 'ok' },
    { at: '08:39:42', title: '确定性规则检查', detail: '可售天数 8 天，低于安全阈值 21 天', status: 'ok' },
    { at: '08:40:00', title: '创建智能体建议', detail: '金额来自已存采购字段，未由 AI 计算', status: 'ok' },
    { at: '08:40:03', title: '等待人工确认', detail: '被代表用户确认后才可进入审批', status: 'warning' },
  ],
  outcome: '待部门主管审批',
}]

const alerts: GapCAlert[] = [{ id: 'alert-001', severity: 'high', title: '权限矩阵修改待二次确认', detail: '管理员修改了 permission:write 的角色范围。', createdAt: '2026-11-10 09:20', resolved: false, href: '/admin/permission-matrix' }, { id: 'alert-002', severity: 'medium', title: '夜间大额审批', detail: '检测到 2026-11-09 23:18 的 ¥80,000 付款审批。', createdAt: '2026-11-10 08:00', resolved: false }]
let retention: GapCRetention = { businessYears: 10, aiYears: 3, archiveAfterDays: 365, lastArchiveAt: '2026-10-01 02:00', immutable: true }
const archiveRuns: GapCArchiveRun[] = [{ id: 'archive-001', policyId: 'policy', startedAt: '2026-10-01 02:00', archivedCount: 128, status: 'simulated', note: '演示归档记录，原始日志保持只追加。' }]

const fieldPolicies: GapCFieldPolicy[] = roleTemplates.flatMap(role => [
  { id: `${role.id}-cost`, roleId: role.id, roleName: role.nameZh, objectType: 'SKU', fieldKey: 'cost', fieldLabel: 'SKU 成本', access: (role.fieldRestrictions.cost ?? 'visible') as FieldAccess, sensitive: true },
  { id: `${role.id}-salary`, roleId: role.id, roleName: role.nameZh, objectType: '工资条', fieldKey: 'salary', fieldLabel: '工资明细', access: (role.fieldRestrictions.salary ?? 'visible') as FieldAccess, sensitive: true },
])

const dataScopes: GapCDataScope[] = roleTemplates.map(role => ({ id: `${role.id}-scope`, roleId: role.id, roleName: role.nameZh, objectType: '业务单据', scope: role.defaultDataScopes[0] ?? 'self', values: role.defaultDataScopes, description: `按${role.defaultDataScopes.join('、')}范围过滤` }))
const temporaryGrants: GapCTemporaryGrant[] = [{ id: 'grant-001', userId: 'demo-operator', userName: '演示运营', permissionKey: 'sku_cost:read', effect: 'allow', reason: '季度盘点临时查看成本', startsAt: '2026-11-10T00:00:00Z', expiresAt: '2026-11-17T00:00:00Z', status: 'active' }]
const accessReviews: GapCAccessReview[] = [{ id: 'review-001', userId: 'demo-operator', userName: '演示运营', reviewer: '演示管理员', dueAt: '2026-12-31', permissionCount: 18, unusedCount: 3, status: 'pending' }, { id: 'review-002', userId: 'demo-finance', userName: '演示财务', reviewer: '演示管理员', dueAt: '2026-12-31', permissionCount: 26, unusedCount: 0, status: 'confirmed' }]
const changes: GapCPermissionChange[] = [{ id: 'chg-001', at: '2026-11-10 09:20', actor: '演示管理员', confirmer: '演示财务主管', target: '运营主管', action: '拒绝导出订单', before: '允许（继承店铺运营）', after: '拒绝（职责限制）', sensitive: true }]
const sodRules: GapCSodRule[] = [{ id: 'sod-001', firstAction: '提交单据', secondAction: '批准单据', objectType: '全部审批单', enabled: true, reason: '做单的人不能审单' }, { id: 'sod-002', firstAction: '新建供应商', secondAction: '发起付款', objectType: '供应商', enabled: true, reason: '职责分离，避免同人控制供应商与付款' }]
const customRoles: GapCRoleView[] = []

function userSubject(): PermissionSubject {
  const session = useSessionStore()

  return subjectFor(session.role, session.userId)
}

function requirePermission(permissionKey: string) {
  const result = effectivePermission(userSubject(), permissionKey)
  if (!result.allowed)
    throw new Error(`当前用户没有权限：${permissionKey}`)

  return actor()
}

const demoDepartments: Record<string, string> = {
  'demo-department-manager': '运营部',
  'demo-employee': '运营部',
  'demo-operator': '运营部',
  'demo-finance': '财务部',
  'demo-purchaser': '供应链部',
}

// 模拟店铺绑定：真实系统应从用户与店铺关联表读取，mock 不代表生产配置。
const demoShopBindings: Record<string, string[]> = {
  'demo-admin': ['shop-cn-01', 'shop-us-01', 'shop-eu-01'],
  'demo-finance': ['shop-cn-01', 'shop-us-01', 'shop-eu-01'],
  'demo-auditor': ['shop-cn-01', 'shop-us-01', 'shop-eu-01'],
  'demo-viewer': ['shop-cn-01'],
  'demo-operator': ['shop-cn-01'],
  'demo-external-viewer': ['shop-eu-01'],
  'demo-store_operator': ['shop-cn-01'],
}

export function dataScopesFor(subject: PermissionSubject, permissionKey: string): DataScopeRuleType[] {
  return effectivePermission(subject, permissionKey).dataScopes
}

export function shopsForSubject(subject: PermissionSubject): string[] {
  return [...(demoShopBindings[subject.userId] ?? [])]
}

export function scopeAllows(subject: PermissionSubject, permissionKey: string, ownerId?: string, department?: string, shopId?: string) {
  const permission = effectivePermission(subject, permissionKey)
  if (!permission.allowed)
    return false
  if (permission.dataScopes.length === 0)
    return false

  const supportedScopes = new Set<DataScopeRuleType>(['all', 'store', 'self', 'owner', 'department'])
  if (permission.dataScopes.some(scope => !supportedScopes.has(scope)))
    return false

  const subjectDepartment = demoDepartments[subject.userId]

  return permission.dataScopes.some(scope => {
    switch (scope) {
      case 'all':
        return true
      case 'store':
        return Boolean(shopId && shopsForSubject(subject).includes(shopId))
      case 'self':
      case 'owner':
        return ownerId === subject.userId
      case 'department':
        return Boolean(department && subjectDepartment && department === subjectDepartment)
      default:
        return false
    }
  })
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function audit(action: string, objectType: string, objectId: string, reason: string) {
  const current = actor()

  writeAudit(database().db, current, action, objectType, objectId, reason)
  aiAudit.unshift({ id: `gap-audit-${Date.now()}`, at: current.at, actor: current.name, actorType: 'human', action, objectType, objectId, reason, ipDevice: 'mock-browser' })
  if (action.startsWith('permission.'))
    changes.unshift({ id: `gap-change-${Date.now()}`, at: current.at, actor: current.name, target: objectId, action, before: '待修改', after: reason, sensitive: true })
  database().persist()
}

export function listGapCApprovals(mode: 'all' | 'agent' | 'cc' = 'all') {
  const current = actor()
  const subject = userSubject()

  const filtered = approvals.filter(item => {
    if (mode === 'agent' && item.origin !== 'agent')
      return false
    if (mode === 'cc' && item.status !== 'cc')
      return false
    if (!scopeAllows(subject, 'approval:read', item.submitterId, item.department, item.shopId))
      return false
    if (current.role === 'employee' || current.role === 'operator')
      return item.submitterId === useSessionStore().userId || item.status === 'cc'

    return true
  })

  return clone(filtered)
}

export function decideGapCApproval(id: string, status: 'approved' | 'rejected') {
  const current = requirePermission('approval:approve')
  const item = approvals.find(row => row.id === id)
  if (!item)
    throw new Error('找不到审批单')
  if (item.submitter === current.name || item.submitterId === useSessionStore().userId)
    throw new Error('不能审批自己提交的单据')
  if (item.status !== 'pending')
    throw new Error('这张审批已经处理过')
  if (item.amount > 5000 && item.nextApprover === '财务主管' && current.role !== 'finance' && current.role !== 'admin')
    throw new Error('该金额需要财务主管审批')
  item.status = status
  audit(status === 'approved' ? 'approval.approve' : 'approval.reject', 'approval', id, `统一审批中心${status === 'approved' ? '批准' : '驳回'} ${item.title}`)

  return clone(item)
}
export function listGapCApprovalRules() {
  requirePermission('approval:read')

  return clone(approvalRules)
}
export function saveGapCApprovalRule(rule: GapCApprovalRule) {
  requirePermission('approval:write')

  const index = approvalRules.findIndex(item => item.id === rule.id); if (index < 0)
    throw new Error('找不到审批规则'); approvalRules[index] = clone(rule); audit('approval.rule.update', 'approval_rule', rule.id, `更新${rule.type}审批额度`)

  return clone(rule)
}

export function listGapCNotifications() {
  requirePermission('notification:read')

  return clone(notifications)
}
export function markGapCNotificationRead(id: string) {
  requirePermission('notification:read')

  const item = notifications.find(row => row.id === id); if (item)
    item.read = true; audit('notification.read', 'notification', id, '查看站内消息')

  return clone(item)
}
export function listGapCSubscriptions() {
  requirePermission('notification:read')

  return clone(subscriptions)
}
export function saveGapCSubscriptions(next: GapCSubscription[]) {
  requirePermission('notification:write'); subscriptions = clone(next); audit('notification.subscription.update', 'notification', 'subscriptions', '更新我的通知订阅')

  return clone(subscriptions)
}

export function listGapCReports() { return clone(reports.filter(report => effectivePermission(userSubject(), report.permissionKey).allowed)) }

function runBuilderReport(builder: GapCReportBuilder, restricted: boolean): Array<Record<string, string | number>> {
  const sourceRows: Record<GapCReportBuilder['dataSource'], Array<Record<string, string | number>>> = {
    orders: [
      { orderNo: 'DE-1001', store: 'Amazon DE', owner: '演示运营', amount: 4200, status: '待发货' },
      { orderNo: 'US-1002', store: 'Amazon US', owner: '演示财务', amount: 8000, status: '已发货' },
    ],
    expenses: [
      { title: '客户拜访住宿', department: '运营部', owner: '演示员工', amount: 2800, status: '待审批' },
      { title: '财务培训', department: '财务部', owner: '演示财务', amount: 1800, status: '已通过' },
    ],
    employees: [
      { name: '演示员工', department: '运营部', salary: restricted ? '***' : 1200000, status: '在职' },
      { name: '演示财务', department: '财务部', salary: restricted ? '***' : 1800000, status: '在职' },
    ],
    audit: aiAudit.map(item => ({ action: item.action, actor: item.actor, object: item.objectId, at: item.at })),
  }

  const filtered = sourceRows[builder.dataSource].filter(row => builder.filters.every(filter => {
    const actual = String(row[filter.field] ?? '')
    if (filter.operator === 'equals')
      return actual === filter.value
    if (filter.operator === 'contains')
      return actual.includes(filter.value)
    const numeric = Number(row[filter.field])
    const expected = Number(filter.value)

    return filter.operator === 'gte' ? numeric >= expected : numeric <= expected
  }))

  if (!builder.fields.length)
    return filtered

  return filtered.map(row => Object.fromEntries(builder.fields.filter(field => field in row).map(field => [field, row[field]])))
}

export function runGapCReport(reportId: string, period: string): GapCReportResult {
  const report = reports.find(item => item.id === reportId)
  if (!report || !effectivePermission(userSubject(), report.permissionKey).allowed)
    throw new Error('当前用户不能运行该报表')
  const restricted = fieldAccess(userSubject(), 'cost') === 'hidden'

  const rows: Array<Record<string, string | number>> = report.builder
    ? runBuilderReport(report.builder, restricted)
    : report.id === 'rpt-budget'
      ? [{ department: '运营部', budget: 100000, used: 82000, rate: '82%', ...(restricted ? {} : { cost: 82000 }) }, { department: '财务部', budget: 120000, used: 51000, rate: '42%' }]
      : report.id === 'rpt-approval'
        ? [{ type: '费用报销', pending: 2, approved: 14, avgHours: 5.2 }, { type: '采购申请', pending: 1, approved: 8, avgHours: 8.5 }]
        : aiAudit.map(item => ({ action: item.action, actor: item.actor, object: item.objectId, at: item.at }))

  const result = { id: `run-${Date.now()}`, reportId, period, rows, generatedAt: new Date().toISOString(), totals: { rows: rows.length } }

  audit('report.run', 'report', reportId, `运行报表 ${report.name}，期间 ${period}`)

  return result
}
export function saveGapCReport(input: { name: string; description: string; permissionKey: string; builder: GapCReportBuilder }) {
  requirePermission('report:write')
  if (!input.name.trim() || !input.builder.dataSource || !input.builder.fields.length)
    throw new Error('报表名称、数据源和字段不能为空')

  const report: GapCReport = { id: `rpt-${Date.now()}`, ...input, module: '自定义', lastRunAt: '未运行', columns: input.builder.fields, builder: clone(input.builder) }

  reports.push(report); audit('report.create', 'report', report.id, `创建自定义报表 ${report.name}`)

  return clone(report)
}

export function listGapCAudit() {
  requirePermission('audit_log:read')

  const dynamic = database().db.audit
    .map(item => ({ id: item.id, at: item.at, actor: item.actor, actorType: 'human' as const, action: item.action, objectType: item.refType, objectId: item.refId, reason: item.summary, ipDevice: 'mock-browser' }))
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at))

  return clone([...dynamic, ...aiAudit])
}
export function getGapCAgentTrace(id: string) {
  requirePermission('audit_log:read')

  return clone(traces.find(item => item.suggestionId === id) ?? traces[0])
}
export function listGapCAlerts() {
  requirePermission('audit_log:read')

  return clone(alerts)
}
export function resolveGapCAlert(id: string) {
  requirePermission('audit_log:write')

  const item = alerts.find(row => row.id === id); if (item)
    item.resolved = true; audit('audit.alert.resolve', 'audit_alert', id, '处理敏感操作告警')

  return clone(item)
}
export function getGapCRetention() {
  requirePermission('audit_log:read')

  return clone(retention)
}
export function saveGapCRetention(next: GapCRetention) {
  requirePermission('audit_log:write')
  if (next.businessYears < 1 || next.aiYears < 1 || next.archiveAfterDays < 1)
    throw new Error('保留期必须为正数')
  retention = clone(next); audit('audit.retention.update', 'audit_retention', 'policy', '更新日志保留策略')

  return clone(retention)
}

export function runGapCArchive(): GapCArchiveRun {
  requirePermission('audit_log:write')

  const run: GapCArchiveRun = { id: `archive-${Date.now()}`, policyId: 'policy', startedAt: new Date().toISOString(), archivedCount: 128, status: 'simulated', note: '模拟归档：只生成执行记录，不删除审计日志。' }

  archiveRuns.unshift(run)
  audit('audit.archive.run', 'audit_archive', run.id, run.note)

  return clone(run)
}

export function listGapCArchiveRuns(): GapCArchiveRun[] {
  requirePermission('audit_log:read')

  return clone(archiveRuns)
}

export function listGapCFieldPolicies() {
  requirePermission('permission:read')

  return clone(fieldPolicies)
}
export function saveGapCFieldPolicy(id: string, access: FieldAccess) {
  requirePermission('permission:write')

  const item = fieldPolicies.find(row => row.id === id); if (!item)
    throw new Error('找不到字段权限'); item.access = access; audit('permission.field.update', 'field_policy', id, `字段 ${item.fieldLabel} 调整为 ${access}`)

  return clone(item)
}
export function listGapCDataScopes() {
  requirePermission('permission:read')

  return clone(dataScopes)
}
export function saveGapCDataScope(id: string, scope: GapCDataScope['scope']) {
  requirePermission('permission:write')

  const item = dataScopes.find(row => row.id === id); if (!item)
    throw new Error('找不到数据范围'); item.scope = scope; audit('permission.scope.update', 'data_scope', id, `数据范围调整为 ${scope}`)

  return clone(item)
}
export function listGapCTemporaryGrants() {
  requirePermission('permission:read')

  return clone(temporaryGrants.map(item => ({ ...item, status: Date.parse(item.expiresAt) > Date.now() ? 'active' : 'expired' })))
}
export function saveGapCTemporaryGrant(input: Omit<GapCTemporaryGrant, 'id' | 'status'>) {
  requirePermission('permission:write')

  const grant = { ...input, id: `grant-${Date.now()}`, status: 'active' as const }

  temporaryGrants.push(grant); audit('permission.temporary_grant.create', 'temporary_grant', grant.id, grant.reason)

  return clone(grant)
}
export function listGapCAccessReviews() {
  requirePermission('permission:read')

  return clone(accessReviews)
}
export function confirmGapCAccessReview(id: string) {
  requirePermission('permission:approve')

  const item = accessReviews.find(row => row.id === id); if (!item)
    throw new Error('找不到权限复核'); item.status = 'confirmed'; audit('permission.access_review.confirm', 'access_review', id, `确认 ${item.userName} 的权限复核`)

  return clone(item)
}
export function listGapCRoles(): GapCRoleView[] {
  requirePermission('permission:read')

  return clone([...roleTemplates.map(role => ({ ...role, memberCount: role.id === 'store_operator' ? 3 : 1, status: 'active' as const })), ...customRoles])
}
export function getGapCRole(id: string) {
  requirePermission('permission:read')

  const role = [...roleTemplates, ...customRoles].find(item => item.id === id); if (!role)
    throw new Error('找不到角色')

  const view: GapCRoleView = 'status' in role && 'memberCount' in role
    ? role as GapCRoleView
    : { ...role, memberCount: role.id === 'store_operator' ? 3 : 1, status: 'active' as const }

  return clone(view)
}
export function copyGapCRole(input: GapCRoleCopyInput): GapCRoleView {
  const current = requirePermission('permission:write')
  const source = [...roleTemplates, ...customRoles].find(item => item.id === input.sourceRoleId)
  if (!source)
    throw new Error('找不到要复制的角色')
  if (!input.nameZh.trim() || !input.nameEn.trim() || !input.dataScopes.length)
    throw new Error('角色名称和数据范围不能为空')

  const role: GapCRoleView = {
    ...clone(source),
    id: `custom_${Date.now()}`,
    nameZh: input.nameZh.trim(),
    nameEn: input.nameEn.trim(),
    parentIds: [source.id],
    defaultDataScopes: [...input.dataScopes],
    memberCount: input.memberUserIds.length,
    memberUserIds: [...input.memberUserIds],
    dataScopeLabel: input.dataScopes.join('、'),
    isCustom: true,
    status: 'active',
  }

  customRoles.push(role)
  audit('permission.role.copy', 'role', role.id, `${current.name} 从 ${source.nameZh} 复制角色 ${role.nameZh}，指派 ${input.memberUserIds.join('、') || '无用户'}`)

  return clone(role)
}
export function listGapCMatrix(): GapCMatrixCell[] {
  requirePermission('permission:read')

  return roleTemplates.flatMap(role => permissionCatalog.slice(0, 40).map(point => ({ roleId: role.id, permissionKey: point.key, effect: role.permissions.some(item => item.permissionKey === point.key && item.effect === 'allow') ? (role.parentIds.length ? 'inherit' : 'allow') : 'none', sensitive: Boolean(point.sensitive) })))
}
export function saveGapCMatrix(cells: GapCMatrixCell[], confirmer?: string) {
  const current = requirePermission('permission:write'); if (cells.some(cell => cell.sensitive) && (!confirmer || confirmer === current.name))
    throw new Error('敏感权限变更需要另一位管理员确认'); audit('permission.matrix.update', 'permission_matrix', 'matrix', `保存 ${cells.length} 个权限格，确认人 ${confirmer ?? '无'}`); changes.unshift({ id: `chg-${Date.now()}`, at: new Date().toISOString(), actor: current.name, confirmer, target: '权限矩阵', action: '批量保存', before: '待修改', after: `${cells.length} 个格子`, sensitive: cells.some(cell => cell.sensitive) })

  return clone(cells)
}
export function listGapCEffective(userId = useSessionStore().userId): GapCEffectiveRow[] {
  requirePermission('permission:read')

  const role = (Object.entries({ 'demo-admin': 'admin', 'demo-operator': 'operator', 'demo-finance': 'finance', 'demo-auditor': 'auditor', 'demo-employee': 'employee', 'demo-purchaser': 'purchaser' }) as Array<[string, Role]>).find(([id]) => id === userId)?.[1] ?? useSessionStore().role; const subject = roleSubject(role, userId)

  return effectivePermission(subject, 'permission:read').allowed ? (permissionCatalog.slice(0, 80).map(point => ({ ...effectivePermission(subject, point.key), labelZh: point.labelZh, module: point.module, sensitive: Boolean(point.sensitive) }))) : []
}
export function listGapCPermissionChanges() {
  requirePermission('permission:read')

  const dynamic = database().db.audit
    .filter(item => item.action.startsWith('permission.'))
    .map(item => ({ id: item.id, at: item.at, actor: item.actor, target: item.refId, action: item.action, before: '待修改', after: item.summary, sensitive: true }))
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at))

  return clone([...dynamic, ...changes])
}
export function listGapCSodRules() {
  requirePermission('permission:read')

  return clone(sodRules)
}
export function saveGapCSodRule(id: string, enabled: boolean) {
  requirePermission('permission:write')

  const item = sodRules.find(row => row.id === id); if (!item)
    throw new Error('找不到职责分离规则'); item.enabled = enabled; audit('permission.sod.update', 'sod_rule', id, `职责分离规则${enabled ? '启用' : '停用'}`)

  return clone(item)
}

export function projectGapCField<T extends Record<string, unknown>>(subject: PermissionSubject, row: T): Partial<T> {
  const result = { ...row }
  const mutable = result as Record<string, unknown>
  for (const key of ['cost', 'margin', 'salary', 'salaryDetail', 'idCard', 'bankAccount', 'buyerContact']) {
    const access = fieldAccess(subject, key)
    if (access === 'hidden')
      delete result[key]
    else if (access === 'masked' && key in result)
      mutable[key] = '***'
  }

  return result
}

export const gapCReadHelpers = { subjectFor, fieldAccess, projectGapCField, dataScopesFor, shopsForSubject, scopeAllows }
