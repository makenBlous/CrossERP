import { validateAutonomyLevel } from '@/utils/autonomy'
import { minorFromDecimal, percentOf } from '@/utils/money'
import { effectivePermission, fieldAccess, roleSubject } from '@/utils/permission-engine'
import { assertHumanActor, requireActorPermission } from '@/utils/service-permissions'
import type { AgentAutonomyLevel } from '@/types/foundation'
import type { Actor } from '@/types/entities'
import type { GapDApprovalRecord, GapDAsset, GapDAuditEvent, GapDContract, GapDDeduction, GapDEmployee, GapDImportRecord, GapDLeaveRequest, GapDMcpServer, GapDPageId, GapDPayrollRule, GapDPayrollRun, GapDPayslip, GapDRecord, GapDTool, GapDWriteOrigin } from '@/types/gap-d'

const now = '2026-11-10T08:00:00+08:00'

export const gapDTools: GapDTool[] = [
  { id: 'tool-profit', name: 'get_profit', kind: 'erp', sideEffect: 'none', enabled: true, readOnly: true, secretConfigured: false, frequencyLimit: 120, autonomyLevel: 'L1', roles: ['*'], lastCallAt: now },
  { id: 'tool-web-search', name: 'web_search', kind: 'web', sideEffect: 'none', enabled: true, readOnly: true, secretConfigured: false, frequencyLimit: 30, autonomyLevel: 'L1', roles: ['admin', 'finance'], lastCallAt: now },
  { id: 'tool-http-demo', name: '供应商库存 HTTP', kind: 'http', sideEffect: 'none', enabled: false, readOnly: true, secretConfigured: false, frequencyLimit: 20, autonomyLevel: 'L1', roles: ['admin'] },
]

export const gapDMcpServers: GapDMcpServer[] = [
  { id: 'mcp-erp-readonly', name: 'ERP 只读 MCP（演示）', transport: 'stdio', endpoint: 'crosserp-mcp-demo', status: 'connected', discoveredTools: ['get_stock', 'get_supplier_score'], imported: false },
]

export const gapDAutonomyPolicies = [
  { id: 'autonomy-receipt', moduleCode: 'expense', action: 'classify_receipt', roleId: '*', level: 'L3' as AgentAutonomyLevel, sideEffect: 'execute_l3' as const, dailyLimit: 20, usedToday: 3, whitelist: true, hardMaxLevel: 'L3' as AgentAutonomyLevel, reason: '票据分类可撤销，白名单动作' },
  { id: 'autonomy-alert', moduleCode: 'expense', action: 'remind_missing_receipt', roleId: '*', level: 'L3' as AgentAutonomyLevel, sideEffect: 'execute_l3' as const, dailyLimit: 50, usedToday: 4, whitelist: true, hardMaxLevel: 'L3' as AgentAutonomyLevel, reason: '内部提醒，不改业务数据' },
  { id: 'autonomy-voucher', moduleCode: 'finance', action: 'draft_voucher', roleId: '*', level: 'L2' as AgentAutonomyLevel, sideEffect: 'propose' as const, dailyLimit: 20, usedToday: 0, whitelist: false, hardMaxLevel: 'L2' as AgentAutonomyLevel, reason: '凭证动作硬上限 L2' },
]

export const gapDDepartments = [
  { id: 'dept-company', name: 'CrossERP', manager: '演示老板/总经理', managerUserId: 'demo-admin', parentId: null },
  { id: 'dept-ops', name: '运营部', manager: '演示运营主管', managerUserId: 'demo-ops-manager', parentId: 'dept-company' },
  { id: 'dept-finance', name: '财务部', manager: '演示财务主管', managerUserId: 'demo-fin-manager', parentId: 'dept-company' },
  { id: 'dept-hr', name: '人事行政部', manager: '演示人事行政', managerUserId: 'demo-admin', parentId: 'dept-company' },
]

export const gapDEmployees: GapDEmployee[] = [
  { id: 'demo-admin', userId: 'demo-admin', name: '演示管理员', department: '人事行政部', title: '系统管理员', email: 'admin@example.test', status: '在职', manager: '演示老板/总经理', managerUserId: 'demo-admin', leaveBalanceDays: 8, salaryCents: 3000000, idNumber: '仅人事可见' },
  { id: 'demo-ops-manager', userId: 'demo-ops-manager', name: '演示运营主管', department: '运营部', title: '运营主管', email: 'ops-manager@example.test', status: '在职', manager: '演示管理员', managerUserId: 'demo-admin', leaveBalanceDays: 8, salaryCents: 2200000, idNumber: '仅人事可见' },
  { id: 'demo-employee', userId: 'demo-employee', name: '演示普通员工', department: '运营部', title: '运营专员', email: 'employee@example.test', status: '在职', manager: '演示运营主管', managerUserId: 'demo-ops-manager', leaveBalanceDays: 5, salaryCents: 1200000, idNumber: '仅人事可见' },
  { id: 'demo-other-employee', userId: 'demo-other-employee', name: '演示其他员工', department: '运营部', title: '运营专员', email: 'other-employee@example.test', status: '在职', manager: '演示运营主管', managerUserId: 'demo-ops-manager', leaveBalanceDays: 5, salaryCents: 1250000, idNumber: '仅人事可见' },
  { id: 'demo-fin-manager', userId: 'demo-fin-manager', name: '演示财务主管', department: '财务部', title: '财务主管', email: 'fin-manager@example.test', status: '在职', manager: '演示管理员', managerUserId: 'demo-admin', leaveBalanceDays: 8, salaryCents: 2400000, idNumber: '仅人事可见' },
  { id: 'demo-finance', userId: 'demo-finance', name: '演示财务', department: '财务部', title: '会计', email: 'finance@example.test', status: '在职', manager: '演示财务主管', managerUserId: 'demo-fin-manager', leaveBalanceDays: 6, salaryCents: 1800000, idNumber: '仅人事可见' },
]

export const gapDContracts: GapDContract[] = [
  { id: 'contract-001', title: '办公场地租赁合同', counterparty: '演示物业公司', effectiveFrom: '2026-01-01', effectiveTo: '2026-12-10', status: '生效', ownerEmployeeId: 'demo-admin', updatedAt: now },
]

export const gapDAssets: GapDAsset[] = [
  { id: 'asset-001', name: 'MacBook Pro 14', status: '可领用', purchaseCents: 1299900, monthlyDepreciationCents: 54163, updatedAt: now },
]

export const gapDLeaveRequests: GapDLeaveRequest[] = [
  { id: 'leave-001', employeeId: 'demo-employee', startDate: '2026-11-16', endDate: '2026-11-17', days: 2, reason: '年假', status: '待主管审批', submittedAt: now, updatedAt: now },
]

export const gapDImportRecords: GapDImportRecord[] = []
export const gapDApprovals: GapDApprovalRecord[] = []

export const gapDPayrollRules: GapDPayrollRule[] = [
  { id: 'rule-shanghai-2026', city: '上海', effectiveFrom: '2026-01-01', pensionRate: 0.08, medicalRate: 0.02, unemploymentRate: 0.005, housingFundRate: 0.07, baseMinCents: 269000, baseMaxCents: 3654900, verified: false },
]

export const gapDDeductions: GapDDeduction[] = [
  { id: 'deduction-001', employeeId: 'demo-employee', employeeName: '演示普通员工', category: '子女教育', monthlyCents: 100000, effectiveFrom: '2026-01-01', status: 'active' },
]

export const gapDPayrollRuns: GapDPayrollRun[] = []
export const gapDAudit: GapDAuditEvent[] = []

const genericRows: Record<string, GapDRecord[]> = {
  G20: [{ id: 'inbox-001', title: '上海供应商发票 INV-2026-001', status: '待识别', owner: '演示普通员工', detail: '上传 PDF，等待确定性字段抽取', updatedAt: now }],
  G21: [{ id: 'alert-001', title: '合同将在 30 天后到期', status: '未读', owner: '演示管理员', detail: '来源：合同有效期规则', updatedAt: now }],
  G22: [{ id: 'trust-001', title: '票据分类', status: '高把握度', detail: '采纳率 96%，基线 90%', updatedAt: now, score: '96%' }],
  G23: [{ id: 'scope-001', title: '普通员工 AI 范围', status: '仅本人', owner: 'employee', detail: '继承当前用户有效权限，禁止联网工具', updatedAt: now }],
  HR04: [{ id: 'onboarding-001', title: '演示普通员工入职清单', status: '进行中', owner: '人事行政部', detail: '账号、资产、交接共 3 项', updatedAt: now }],
  HR05: [{ id: 'attendance-001', title: '2026-11-09 打卡异常', status: '待解释', owner: '演示普通员工', detail: '下班打卡缺失', updatedAt: now }],
  HR06: [{ id: 'leave-001', title: '演示普通员工年假申请', status: '待审批', owner: '演示普通员工', detail: '2026-11-16 至 2026-11-17，共 2 天', updatedAt: now }],
  AM01: [{ id: 'contract-001', title: '办公场地租赁合同', status: '生效', owner: '人事行政部', detail: '到期日 2026-12-10', updatedAt: now }],
  AM02: [{ id: 'asset-001', title: 'MacBook Pro 14', status: '已领用', owner: '演示普通员工', amount: 12999, currency: 'CNY', detail: '月折旧 541.63', updatedAt: now }],
  AM04: [{ id: 'announcement-001', title: '年末盘点安排', status: '已发布', owner: '人事行政部', detail: '请各部门按清单完成盘点', updatedAt: now }],
  AM05: [{ id: 'supply-001', title: 'A4 复印纸', status: '可领用', owner: '行政仓', detail: '库存 12 箱，安全库存 5 箱', updatedAt: now }],
}

const GAP_D_STORAGE_KEY = 'crosserp-gapd-v1'
let hydrated = false

function persistGapDState() {
  if (typeof localStorage === 'undefined')
    return

  localStorage.setItem(GAP_D_STORAGE_KEY, JSON.stringify({
    tools: gapDTools,
    mcpServers: gapDMcpServers,
    policies: gapDAutonomyPolicies,
    departments: gapDDepartments,
    employees: gapDEmployees,
    contracts: gapDContracts,
    assets: gapDAssets,
    leaves: gapDLeaveRequests,
    imports: gapDImportRecords,
    approvals: gapDApprovals,
    payrollRules: gapDPayrollRules,
    deductions: gapDDeductions,
    payrollRuns: gapDPayrollRuns,
    audit: gapDAudit,
    genericRows,
  }))
}

function hydrateGapDState() {
  if (hydrated || typeof localStorage === 'undefined')
    return
  hydrated = true
  try {
    const raw = localStorage.getItem(GAP_D_STORAGE_KEY)
    if (!raw)
      return
    const saved = JSON.parse(raw) as Partial<Record<string, unknown>>
    for (const [key, target] of [['tools', gapDTools], ['mcpServers', gapDMcpServers], ['policies', gapDAutonomyPolicies], ['departments', gapDDepartments], ['employees', gapDEmployees], ['contracts', gapDContracts], ['assets', gapDAssets], ['leaves', gapDLeaveRequests], ['imports', gapDImportRecords], ['approvals', gapDApprovals], ['payrollRules', gapDPayrollRules], ['deductions', gapDDeductions], ['payrollRuns', gapDPayrollRuns], ['audit', gapDAudit]] as const) {
      const source = saved[key]
      if (Array.isArray(source))
        target.splice(0, target.length, ...source as never[])
    }
    if (saved.genericRows && typeof saved.genericRows === 'object') {
      for (const [key, rows] of Object.entries(saved.genericRows as Record<string, unknown>)) {
        if (Array.isArray(rows))
          genericRows[key] = rows as GapDRecord[]
      }
    }
  }
  catch {
    localStorage.removeItem(GAP_D_STORAGE_KEY)
  }
}

hydrateGapDState()

function addAudit(action: string, actor: Actor, detail: string, origin: 'human' | 'ai' | 'system' = 'human', agentSuggestionId?: string) {
  gapDAudit.unshift({ id: `gapd-audit-${Date.now()}`, action, origin, agentSuggestionId, actor: actor.name, at: new Date().toISOString(), detail })
}

export const gapDPermissionKeys = {
  employeeSalaryRead: 'employee.salary:read',
  employeeIdNumberRead: 'employee.id_number:read',
  payrollCalculate: 'payroll_run:calculate',
  payrollApprove: 'salary_slip:approve',
  payslipReadOwn: 'salary_slip:read_own',
  payslipReadAll: 'salary_slip:read_all',
  employeeRecordRead: 'employee_record:read',
  employeeRecordWrite: 'employee_record:write',
  attendanceWrite: 'attendance:write',
  leaveCreate: 'leave_application:create',
  leaveApproveManager: 'leave_application:approve_manager',
  leaveApproveHr: 'leave_application:approve_hr',
  contractWrite: 'contract:write',
  assetWrite: 'asset:write',
  toolCreate: 'agent_tool:create',
  toolWrite: 'agent_tool:write',
  payrollReview: 'salary_slip:review',
  payslipPublish: 'salary_slip:write',
} as const

function permission(actor: Actor, permissionKey: string) {
  return effectivePermission(roleSubject(actor.role, actor.userId), permissionKey)
}

function hasScope(actor: Actor, permissionKey: string, scope: 'all' | 'self') {
  const result = permission(actor, permissionKey)

  return result.allowed && result.dataScopes.includes(scope)
}

function requireScope(actor: Actor, permissionKey: string, scope: 'all' | 'self' = 'all') {
  const result = requireActorPermission(actor, permissionKey)
  if (!result.dataScopes.includes(scope))
    throw new Error(`当前用户的数据范围不包含：${scope}`)

  return result
}

function writeGuard(actor: Actor, permissionKey: string, origin: GapDWriteOrigin = 'human') {
  assertHumanActor(origin)

  return requireActorPermission(actor, permissionKey)
}

function isOwnEmployee(employee: GapDEmployee, actor: Actor) {
  return Boolean(actor.userId) && employee.userId === actor.userId
}

function canReadEmployeeField(employee: GapDEmployee, actor: Actor, permissionKey: string) {
  const fieldKey = permissionKey === gapDPermissionKeys.employeeSalaryRead ? 'salary' : 'idCard'
  const access = fieldAccess(roleSubject(actor.role, actor.userId), fieldKey)

  return access !== 'hidden' && (hasScope(actor, permissionKey, 'all') || (hasScope(actor, permissionKey, 'self') && isOwnEmployee(employee, actor)))
}

function visibleEmployees(actor: Actor) {
  const result = permission(actor, gapDPermissionKeys.employeeRecordRead)
  const ownResult = permission(actor, 'employee_record:read_own')
  if (!result.allowed && !ownResult.allowed)
    return []
  if (!result.allowed && ownResult.dataScopes.includes('self')) {
    const own = gapDEmployees.find(employee => isOwnEmployee(employee, actor))

    return own ? [own] : []
  }
  if (result.dataScopes.includes('all'))
    return gapDEmployees
  if (result.dataScopes.includes('self'))
    return gapDEmployees.filter(employee => isOwnEmployee(employee, actor))
  if (result.dataScopes.includes('department')) {
    const own = gapDEmployees.find(employee => isOwnEmployee(employee, actor))

    return own ? gapDEmployees.filter(employee => employee.department === own.department) : []
  }

  return []
}

function findEmployee(employeeId: string) {
  return gapDEmployees.find(employee => employee.id === employeeId)
}

function findEmployeeByUserId(userId: string) {
  return gapDEmployees.find(employee => employee.userId === userId)
}

function ownPayslips(run: GapDPayrollRun, actor: Actor) {
  return run.payslips.filter(payslip => {
    const employee = findEmployee(payslip.employeeId)

    return employee ? isOwnEmployee(employee, actor) : payslip.employeeUserId === actor.userId
  })
}

function filteredPayrollRun(run: GapDPayrollRun, payslips: GapDPayslip[]): GapDPayrollRun {
  return { ...run, employeeCount: payslips.length, payslips }
}

export function listGapDRecords(pageId: GapDPageId, actor: Actor): GapDRecord[] {
  if (pageId === 'HR01')
    return gapDDepartments.map(row => ({ id: row.id, title: row.name, status: row.parentId ? '子部门' : '根部门', owner: row.manager, detail: row.parentId ? '上级：CrossERP' : '组织根节点', updatedAt: now }))
  if (pageId === 'HR02') {
    return visibleEmployees(actor).map(row => {
      const canSeeSalary = canReadEmployeeField(row, actor, gapDPermissionKeys.employeeSalaryRead)
      const canSeeIdNumber = canReadEmployeeField(row, actor, gapDPermissionKeys.employeeIdNumberRead)
      const safeRow = { ...row }

      delete safeRow.salaryCents
      delete safeRow.idNumber

      return {
        ...safeRow,
        title: row.name,
        status: row.status,
        updatedAt: now,
        ...(canSeeSalary ? { salaryCents: row.salaryCents } : {}),
        ...(canSeeIdNumber ? { idNumber: row.idNumber } : {}),
      }
    })
  }
  if (pageId === 'AM01')
    return gapDContracts.map(row => ({ id: row.id, title: row.title, status: row.status, owner: row.counterparty, detail: `${row.effectiveFrom} 至 ${row.effectiveTo}`, updatedAt: row.updatedAt }))
  if (pageId === 'AM02' || pageId === 'AM03')
    return gapDAssets.map(row => ({ id: row.id, title: row.name, status: row.status, owner: row.holderEmployeeId, amount: row.purchaseCents / 100, currency: 'CNY', detail: `月折旧 ${row.monthlyDepreciationCents / 100}`, updatedAt: row.updatedAt }))
  if (pageId === 'HR06')
    return gapDLeaveRequests.map(row => ({ id: row.id, title: `${row.startDate} 至 ${row.endDate} 请假`, status: row.status, owner: row.employeeId, detail: `${row.days} 天：${row.reason}`, updatedAt: row.updatedAt }))
  if (pageId === 'HR05')
    return gapDImportRecords.filter(row => row.kind === 'attendance').map(row => ({ id: row.id, title: row.fileName, status: row.status, owner: row.createdBy, detail: `登记 ${row.rowCount} 行，不存文件`, updatedAt: row.createdAt }))
  if (pageId === 'HR12') {
    if (!hasScope(actor, gapDPermissionKeys.payslipReadOwn, 'self'))
      return []

    const own = gapDPayrollRuns.flatMap(run => ownPayslips(run, actor))

    return own.map(row => ({ id: row.id, title: `${row.period} 工资条`, status: row.status, owner: row.employeeName, amount: row.netCents / 100, currency: 'CNY', detail: `实发 ¥${(row.netCents / 100).toFixed(2)}，个税仅本人可见`, updatedAt: now }))
  }
  if (pageId === 'G18')
    return gapDAutonomyPolicies.map(row => ({ ...row, id: row.id, title: row.action, status: row.level, detail: row.reason, updatedAt: now }))
  if (pageId === 'G04' || pageId === 'G24' || pageId === 'G25' || pageId === 'G26')
    return pageId === 'G26' ? gapDMcpServers.map(row => ({ ...row, id: row.id, title: row.name, status: row.status, detail: `${row.transport} · ${row.discoveredTools.length} 个工具`, updatedAt: now })) : gapDTools.map(row => ({ ...row, id: row.id, title: row.name, status: row.enabled ? '已启用' : '已停用', detail: `${row.readOnly ? '只读' : '可写'} · 频率上限 ${row.frequencyLimit}/日`, updatedAt: now }))

  return genericRows[pageId] ?? [{ id: `${pageId.toLowerCase()}-001`, title: `${pageId} 演示记录`, status: '进行中', owner: actor.name, detail: '静态演示数据，后端接入后由接口替换', updatedAt: now }]
}

export function updateGapDAutonomy(id: string, requested: AgentAutonomyLevel, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, gapDPermissionKeys.toolWrite, origin)

  const policy = gapDAutonomyPolicies.find(row => row.id === id)
  if (!policy)
    throw new Error('自治策略不存在')
  const result = validateAutonomyLevel(policy.action, requested, policy.hardMaxLevel)
  if (!result.ok)
    throw new Error(result.reason)
  policy.level = result.level
  addAudit('更新自主等级', actor, `${policy.action} → ${result.level}`)
  persistGapDState()

  return policy
}

export function updateGapDAiMode(mode: 'normal' | 'degraded' | 'off', reason: string, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, 'agent_mode:write', origin)
  addAudit('切换 AI 总开关', actor, `${mode}：${reason}`)
  persistGapDState()

  return { mode, changedAt: new Date().toISOString(), changedBy: actor.name, reason }
}

export function saveGapDTool(input: Partial<GapDTool>, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, gapDPermissionKeys.toolCreate, origin)
  if (input.frequencyLimit !== undefined && (!Number.isInteger(input.frequencyLimit) || input.frequencyLimit < 1 || input.frequencyLimit > 10000))
    throw new Error('频率上限必须是 1 到 10000 的整数')
  const tool: GapDTool = { id: input.id ?? `tool-${Date.now()}`, name: input.name ?? '自定义 HTTP 工具', kind: input.kind ?? 'http', sideEffect: 'none', enabled: false, readOnly: true, secretConfigured: Boolean(input.secretConfigured), frequencyLimit: input.frequencyLimit ?? 20, autonomyLevel: 'L1', roles: input.roles ?? ['admin'], endpoint: input.endpoint }
  const existing = gapDTools.findIndex(row => row.id === tool.id)
  if (existing >= 0)
    gapDTools[existing] = { ...gapDTools[existing], ...tool }
  else
    gapDTools.push(tool)
  addAudit('保存智能体工具', actor, `${tool.name} 默认停用、只读`)
  persistGapDState()

  return tool
}

export function toggleGapDTool(id: string, enabled: boolean, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, gapDPermissionKeys.toolWrite, origin)

  const tool = gapDTools.find(row => row.id === id)
  if (!tool)
    throw new Error('工具不存在')
  tool.enabled = enabled
  addAudit(enabled ? '启用智能体工具' : '停用智能体工具', actor, `${tool.name}：${enabled ? '启用' : '停用'}`)
  persistGapDState()

  return tool
}

export function configureGapDTool(id: string, input: { secretConfigured?: boolean; frequencyLimit?: number }, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, gapDPermissionKeys.toolWrite, origin)

  const tool = gapDTools.find(row => row.id === id)
  if (!tool)
    throw new Error('工具不存在')
  if (input.frequencyLimit !== undefined && (!Number.isInteger(input.frequencyLimit) || input.frequencyLimit < 1 || input.frequencyLimit > 10000))
    throw new Error('频率上限必须是 1 到 10000 的整数')
  if (input.secretConfigured !== undefined)
    tool.secretConfigured = input.secretConfigured
  if (input.frequencyLimit !== undefined)
    tool.frequencyLimit = input.frequencyLimit
  addAudit('配置智能体工具', actor, `${tool.name}：密钥${tool.secretConfigured ? '已配置' : '未配置'}，频率上限 ${tool.frequencyLimit}`, origin)
  persistGapDState()

  return tool
}

export function testGapDTool(id: string, actor: Actor) {
  requireActorPermission(actor, gapDPermissionKeys.toolWrite)

  const tool = gapDTools.find(row => row.id === id)
  if (!tool)
    throw new Error('工具不存在')
  if (!tool.enabled)
    throw new Error('工具已停用，不能测试调用')
  if (tool.kind === 'http' && !tool.secretConfigured)
    throw new Error('HTTP 工具尚未配置密钥')
  tool.lastCallAt = new Date().toISOString()
  addAudit('测试调用智能体工具', actor, `${tool.name}：模拟只读响应，带出处 https://example.test/mock-source`)
  persistGapDState()

  return { ok: true, citation: 'https://example.test/mock-source', readOnly: tool.readOnly }
}

export function registerGapDMcpServer(input: Omit<GapDMcpServer, 'id' | 'status' | 'imported'> & { id?: string }, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, gapDPermissionKeys.toolWrite, origin)
  if (!input.name.trim() || !input.endpoint.trim())
    throw new Error('MCP 服务器名称和地址不能为空')
  if (gapDMcpServers.some(row => row.name === input.name.trim()))
    throw new Error('MCP 服务器已登记，重复登记被拒绝')
  const server: GapDMcpServer = { ...input, id: input.id ?? `mcp-${Date.now()}`, name: input.name.trim(), endpoint: input.endpoint.trim(), status: 'disabled', imported: false }

  gapDMcpServers.unshift(server)
  addAudit('登记 MCP 服务器', actor, `${server.name} 默认停用`, origin)
  persistGapDState()

  return server
}

export function ingestGapDInbox(fileName: string, actor: Actor) {
  requireActorPermission(actor, 'agent_tool:create')

  const record: GapDRecord = { id: `inbox-${Date.now()}`, title: fileName, status: '待识别', owner: actor.name, detail: '文件已收件，等待确定性字段抽取', updatedAt: new Date().toISOString() }

  genericRows.G20 = [record, ...(genericRows.G20 ?? [])]
  addAudit('上传票据', actor, fileName)
  persistGapDState()

  return record
}

export function importGapDMcpTool(serverId: string, actor: Actor) {
  writeGuard(actor, gapDPermissionKeys.toolWrite)

  const server = gapDMcpServers.find(row => row.id === serverId)
  if (!server)
    throw new Error('MCP 服务器不存在')
  for (const name of server.discoveredTools)
    saveGapDTool({ id: `mcp-${server.id}-${name}`, name, kind: 'mcp', roles: ['admin'] }, actor)
  server.imported = true
  addAudit('导入 MCP 工具', actor, `${server.name}：${server.discoveredTools.join('、')}`)
  persistGapDState()

  return server
}

export function calculateCumulativeTax(taxableCumulativeCents: number, months: number, previousTaxCents = 0) {
  const annual = Math.max(0, taxableCumulativeCents - 6000000 * months)
  const brackets: Array<[number, number, number]> = [[3600000, 0.03, 0], [14400000, 0.1, 25200], [30000000, 0.2, 169200]]
  let rate = 0.25
  let quick = 319200
  for (const [limit, candidate, deduction] of brackets) {
    if (annual <= limit) {
      rate = candidate
      quick = deduction
      break
    }
  }

  return Math.max(0, Math.round(annual * rate - quick) - previousTaxCents)
}

export function calculateGapDPayroll(period: string, actor: Actor) {
  requireScope(actor, gapDPermissionKeys.payrollCalculate, 'all')
  if (!/^\d{4}-(?:0[1-9]|1[0-2])$/.test(period))
    throw new Error('算薪期间格式必须为 YYYY-MM')
  if (gapDPayrollRuns.some(row => row.period === period))
    throw new Error('该期间已经发起算薪，重复提交被拒绝')
  const rule = gapDPayrollRules[0]
  const month = Number(period.slice(5, 7)) || 1

  const payslips: GapDPayslip[] = gapDEmployees.filter(row => row.status !== '离职').map(employee => {
    const grossCents = employee.salaryCents ?? 0
    const base = Math.min(rule.baseMaxCents, Math.max(rule.baseMinCents, grossCents))

    const socialMinor = percentOf(base * 100, minorFromDecimal(String(rule.pensionRate)))
      + percentOf(base * 100, minorFromDecimal(String(rule.medicalRate)))
      + percentOf(base * 100, minorFromDecimal(String(rule.unemploymentRate)))

    const housingMinor = percentOf(base * 100, minorFromDecimal(String(rule.housingFundRate)))
    const social = Math.round(socialMinor / 100)
    const housing = Math.round(housingMinor / 100)
    const taxable = grossCents - social - housing
    const tax = calculateCumulativeTax(taxable, month)

    return { id: `payslip-${period}-${employee.id}`, employeeId: employee.id, employeeUserId: employee.userId, employeeName: employee.name, period, grossCents, socialPersonalCents: social, housingFundPersonalCents: housing, taxableCumulativeCents: taxable, taxCents: tax, netCents: grossCents - social - housing - tax, ruleVersion: `${rule.city}/${rule.effectiveFrom}`, status: '待复核' }
  })

  const run: GapDPayrollRun = { id: `payroll-${period}`, period, status: '待复核', employeeCount: payslips.length, payslips, createdAt: new Date().toISOString() }
  const index = gapDPayrollRuns.findIndex(row => row.id === run.id)
  if (index >= 0)
    gapDPayrollRuns[index] = run
  else
    gapDPayrollRuns.push(run)
  addAudit('发起算薪', actor, `${period}，${payslips.length} 人，按累计预扣法确定性计算`)
  persistGapDState()

  return run
}

export function getGapDPayrollRun(id: string, actor: Actor): GapDPayrollRun | null {
  const run = gapDPayrollRuns.find(row => row.id === id)
  if (!run)
    return null
  const canReadAll = hasScope(actor, gapDPermissionKeys.payslipReadAll, 'all') || hasScope(actor, gapDPermissionKeys.payrollApprove, 'all')

  if (canReadAll)
    return filteredPayrollRun(run, run.payslips)

  if (hasScope(actor, gapDPermissionKeys.payslipReadOwn, 'self'))
    return filteredPayrollRun(run, ownPayslips(run, actor))

  return null
}

const operationPermission: Partial<Record<GapDPageId, string>> = {
  HR01: gapDPermissionKeys.employeeRecordWrite,
  HR04: gapDPermissionKeys.employeeRecordWrite,
  HR05: gapDPermissionKeys.attendanceWrite,
  G21: 'notification:write',
  G22: gapDPermissionKeys.toolWrite,
  G23: gapDPermissionKeys.toolWrite,
  AM01: gapDPermissionKeys.contractWrite,
  AM02: gapDPermissionKeys.assetWrite,
  AM05: 'office_supply:create',
}

export function saveGapDRecord(pageId: GapDPageId, input: { title: string; detail?: string }, actor: Actor, origin: GapDWriteOrigin = 'human') {
  const permissionKey = operationPermission[pageId]
  if (!permissionKey)
    throw new Error(`页面 ${pageId} 没有可写入的操作契约`)
  writeGuard(actor, permissionKey, origin)

  const title = input.title.trim()
  if (!title)
    throw new Error('标题不能为空')
  const duplicate = (genericRows[pageId] ?? []).some(row => row.title === title && row.status === '待处理')
  if (duplicate)
    throw new Error('相同待处理记录已存在，重复提交被拒绝')
  const record: GapDRecord = { id: `${pageId.toLowerCase()}-${Date.now()}`, title, status: '待处理', owner: actor.userId, detail: input.detail?.trim() || '人工创建的待处理记录', updatedAt: new Date().toISOString() }

  genericRows[pageId] = [record, ...(genericRows[pageId] ?? [])]
  addAudit(`保存 ${pageId} 记录`, actor, `${title}（模拟）`, origin)
  persistGapDState()

  return record
}

export function transitionGapDEmployeeStatus(employeeId: string, status: GapDEmployee['status'], actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, gapDPermissionKeys.employeeRecordWrite, origin)

  const employee = findEmployee(employeeId)
  if (!employee)
    throw new Error('员工不存在')
  if (employee.status === status)
    throw new Error('员工已经处于该状态，重复流转被拒绝')
  employee.status = status
  addAudit('员工入离职状态流转', actor, `${employee.id} → ${status}`, origin)
  persistGapDState()

  return employee
}

export function editGapDContract(contractId: string, input: Partial<Pick<GapDContract, 'title' | 'counterparty' | 'effectiveFrom' | 'effectiveTo' | 'status'>>, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, gapDPermissionKeys.contractWrite, origin)

  const contract = gapDContracts.find(row => row.id === contractId)
  if (!contract)
    throw new Error('合同不存在')
  const next = { ...contract, ...input, updatedAt: new Date().toISOString() }
  if (JSON.stringify(next) === JSON.stringify(contract))
    throw new Error('合同没有变化，重复提交被拒绝')
  Object.assign(contract, next)
  addAudit('编辑合同', actor, `${contract.title}（模拟）`, origin)
  persistGapDState()

  return contract
}

export function checkoutGapDAsset(assetId: string, employeeId: string, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, gapDPermissionKeys.assetWrite, origin)

  const asset = gapDAssets.find(row => row.id === assetId)
  const employee = findEmployee(employeeId)
  if (!asset || !employee)
    throw new Error('资产或员工不存在')
  if (asset.status !== '可领用')
    throw new Error('资产当前不可领用')
  asset.status = '已领用'
  asset.holderEmployeeId = employee.id
  asset.updatedAt = new Date().toISOString()
  addAudit('资产领用', actor, `${asset.name} → ${employee.id}`, origin)
  persistGapDState()

  return asset
}

export function returnGapDAsset(assetId: string, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, gapDPermissionKeys.assetWrite, origin)

  const asset = gapDAssets.find(row => row.id === assetId)
  if (!asset)
    throw new Error('资产不存在')
  if (asset.status !== '已领用')
    throw new Error('资产当前不是领用状态，重复归还被拒绝')
  asset.status = '已归还'
  asset.holderEmployeeId = undefined
  asset.updatedAt = new Date().toISOString()
  addAudit('资产归还', actor, asset.name, origin)
  persistGapDState()

  return asset
}

export function submitGapDLeave(input: { employeeId?: string; startDate: string; endDate: string; reason: string }, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, gapDPermissionKeys.leaveCreate, origin)

  const employeeId = input.employeeId ?? gapDEmployees.find(row => isOwnEmployee(row, actor))?.id
  if (!employeeId || employeeId !== gapDEmployees.find(row => isOwnEmployee(row, actor))?.id)
    throw new Error('只能提交本人请假申请')
  if (input.endDate < input.startDate)
    throw new Error('请假结束日期不能早于开始日期')
  if (!input.reason.trim())
    throw new Error('请假原因不能为空')
  if (gapDLeaveRequests.some(row => row.employeeId === employeeId && row.startDate === input.startDate && row.endDate === input.endDate && row.status !== '已驳回'))
    throw new Error('相同日期的请假申请已存在，重复提交被拒绝')
  const days = Math.max(1, Math.round((Date.parse(`${input.endDate}T00:00:00Z`) - Date.parse(`${input.startDate}T00:00:00Z`)) / 86400000) + 1)
  const request: GapDLeaveRequest = { id: `leave-${Date.now()}`, employeeId, startDate: input.startDate, endDate: input.endDate, days, reason: input.reason.trim(), status: '待主管审批', submittedAt: new Date().toISOString(), updatedAt: new Date().toISOString() }

  gapDLeaveRequests.unshift(request)
  addAudit('提交请假', actor, `${employeeId}：${request.days} 天`, origin)
  persistGapDState()

  return request
}

export function approveGapDLeave(id: string, actor: Actor, origin: GapDWriteOrigin = 'human') {
  assertHumanActor(origin)

  const request = gapDLeaveRequests.find(row => row.id === id)
  if (!request)
    throw new Error('请假申请不存在')
  const employee = findEmployee(request.employeeId)
  if (!employee)
    throw new Error('申请员工不存在')
  if (actor.userId === employee.userId)
    throw new Error('不能审批自己提交的请假')

  if (request.status === '待主管审批') {
    const managerPermission = permission(actor, gapDPermissionKeys.leaveApproveManager)
    if (!managerPermission.allowed)
      throw new Error(`当前用户没有权限：${gapDPermissionKeys.leaveApproveManager}；请先由部门主管审批，财务不能跳过主管`)
    const approver = findEmployeeByUserId(actor.userId)
    if (!employee.department || !employee.managerUserId || !approver?.department)
      throw new Error('申请员工或审批人缺少部门/直属主管绑定')
    const sameDepartment = managerPermission.dataScopes.includes('department') && approver.department === employee.department
    const directManager = actor.userId === employee.managerUserId
    if (!managerPermission.dataScopes.includes('all') && !sameDepartment && !directManager)
      throw new Error('审批人的数据范围不包含申请员工所在部门')
    request.managerApprovedBy = actor.userId
    request.status = '待人事审批'
  }
  else if (request.status === '待人事审批') {
    const hrPermission = permission(actor, gapDPermissionKeys.leaveApproveHr)
    if (!hrPermission.allowed)
      throw new Error(`当前用户没有权限：${gapDPermissionKeys.leaveApproveHr}；请先由人事审批，财务不能跳过人事`)
    request.hrApprovedBy = actor.userId
    request.status = '已批准'
  }
  else {
    throw new Error('请假申请已处理，重复审批被拒绝')
  }
  request.updatedAt = new Date().toISOString()
  gapDApprovals.push({ id: `approval-${Date.now()}`, targetType: 'leave', targetId: id, level: request.status === '待人事审批' ? 1 : 2, approverUserId: actor.userId, status: 'approved', decidedAt: request.updatedAt })
  addAudit('审批请假', actor, `${id} → ${request.status}`, origin)
  persistGapDState()

  return request
}

export function registerGapDImport(kind: GapDImportRecord['kind'], fileName: string, rowCount: number, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, kind === 'attendance' ? gapDPermissionKeys.attendanceWrite : gapDPermissionKeys.contractWrite, origin)
  if (!fileName.trim() || !Number.isInteger(rowCount) || rowCount < 1)
    throw new Error('模拟导入需要文件名和正整数行数')
  if (gapDImportRecords.some(row => row.kind === kind && row.fileName === fileName.trim()))
    throw new Error('相同文件已登记，重复导入被拒绝')
  const record: GapDImportRecord = { id: `import-${Date.now()}`, kind, fileName: fileName.trim(), rowCount, status: '已登记', createdBy: actor.userId, createdAt: new Date().toISOString() }

  gapDImportRecords.unshift(record)
  addAudit(kind === 'attendance' ? '登记考勤模拟导入' : '登记合同模拟导入', actor, `${record.fileName}，${rowCount} 行`, origin)
  persistGapDState()

  return record
}

export function saveGapDPayrollRule(input: Omit<GapDPayrollRule, 'id' | 'verified'> & { id?: string }, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, 'salary_structure:write', origin)
  if (!input.city.trim() || !input.effectiveFrom)
    throw new Error('规则城市和生效日不能为空')
  const existing = input.id ? gapDPayrollRules.find(row => row.id === input.id) : undefined
  if (existing) {
    Object.assign(existing, { ...input, verified: false })
  }
  else {
    const rule: GapDPayrollRule = { ...input, id: input.id ?? `rule-${Date.now()}`, verified: false }

    gapDPayrollRules.unshift(rule)
  }
  addAudit('保存社保个税模拟规则', actor, `${input.city}（待会计/HR 核实）`, origin)
  persistGapDState()

  return existing ?? gapDPayrollRules[0]
}

export function saveGapDDeduction(input: Omit<GapDDeduction, 'id' | 'status' | 'employeeName'> & { id?: string }, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, 'employee_tax_exemption_declaration:create', origin)

  const employee = findEmployee(input.employeeId)
  if (!employee)
    throw new Error('员工不存在')
  const row: GapDDeduction = { ...input, id: input.id ?? `deduction-${Date.now()}`, employeeName: employee.name, status: 'pending' }
  const index = gapDDeductions.findIndex(item => item.id === row.id)
  if (index >= 0)
    throw new Error('专项附加扣除记录已存在，重复提交被拒绝')
  gapDDeductions.unshift(row)
  addAudit('保存专项附加扣除', actor, `${employee.id}：${row.category}`, origin)
  persistGapDState()

  return row
}

export function reviewGapDPayroll(runId: string, reason: string, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, gapDPermissionKeys.payrollReview, origin)

  const run = gapDPayrollRuns.find(row => row.id === runId)
  if (!run)
    throw new Error('薪资批次不存在')
  if (run.status !== '待复核')
    throw new Error('薪资批次当前不可复核，重复复核被拒绝')
  if (!reason.trim())
    throw new Error('复核原因不能为空')
  run.status = '待审批'
  run.reviewedBy = actor.userId
  gapDApprovals.push({ id: `approval-${Date.now()}`, targetType: 'payroll', targetId: run.id, level: 1, approverUserId: actor.userId, status: 'approved', decidedAt: new Date().toISOString() })
  addAudit('薪资复核提交审批', actor, `${run.id}：${reason.trim()}`, origin)
  persistGapDState()

  return run
}

export function approveGapDPayroll(runId: string, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, gapDPermissionKeys.payrollApprove, origin)

  const run = gapDPayrollRuns.find(row => row.id === runId)
  if (!run)
    throw new Error('薪资批次不存在')
  if (run.status !== '待审批')
    throw new Error('薪资批次必须先完成人事复核，不能跳级审批')
  if (actor.userId === run.reviewedBy)
    throw new Error('不能由复核人自审批薪资批次')
  run.status = '已出凭证'
  run.approvedBy = actor.userId
  gapDApprovals.push({ id: `approval-${Date.now()}`, targetType: 'payroll', targetId: run.id, level: 2, approverUserId: actor.userId, status: 'approved', decidedAt: new Date().toISOString() })
  addAudit('财务审批薪资批次', actor, run.id, origin)
  persistGapDState()

  return run
}

export function publishGapDPayslips(runId: string, actor: Actor, origin: GapDWriteOrigin = 'human') {
  writeGuard(actor, gapDPermissionKeys.payslipPublish, origin)

  const run = gapDPayrollRuns.find(row => row.id === runId)
  if (!run)
    throw new Error('薪资批次不存在')
  if (run.status !== '已出凭证' || !run.approvedBy)
    throw new Error('薪资批次尚未完成财务审批')
  if (run.publishedAt)
    throw new Error('工资条已经发布，重复发布被拒绝')
  run.publishedAt = new Date().toISOString()
  addAudit('发布工资条', actor, run.id, origin)
  persistGapDState()

  return run
}

export function listGapDAudit() {
  return gapDAudit
}
