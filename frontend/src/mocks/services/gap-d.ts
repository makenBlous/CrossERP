import { validateAutonomyLevel } from '@/utils/autonomy'
import { effectivePermission, roleSubject } from '@/utils/permission-engine'
import type { AgentAutonomyLevel } from '@/types/foundation'
import type { Actor } from '@/types/entities'
import type { GapDAuditEvent, GapDDeduction, GapDEmployee, GapDMcpServer, GapDPageId, GapDPayrollRule, GapDPayrollRun, GapDPayslip, GapDRecord, GapDTool } from '@/types/gap-d'

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
  { id: 'dept-company', name: 'CrossERP', manager: '演示老板/总经理', parentId: null },
  { id: 'dept-ops', name: '运营部', manager: '演示运营主管', parentId: 'dept-company' },
  { id: 'dept-finance', name: '财务部', manager: '演示财务主管', parentId: 'dept-company' },
  { id: 'dept-hr', name: '人事行政部', manager: '演示人事行政', parentId: 'dept-company' },
]

export const gapDEmployees: GapDEmployee[] = [
  { id: 'demo-admin', userId: 'demo-admin', name: '演示管理员', department: '人事行政部', title: '系统管理员', email: 'admin@example.test', status: '在职', manager: '演示老板/总经理', leaveBalanceDays: 8, salaryCents: 3000000, idNumber: '仅人事可见' },
  { id: 'demo-employee', userId: 'demo-employee', name: '演示普通员工', department: '运营部', title: '运营专员', email: 'employee@example.test', status: '在职', manager: '演示运营主管', leaveBalanceDays: 5, salaryCents: 1200000, idNumber: '仅人事可见' },
  { id: 'demo-finance', userId: 'demo-finance', name: '演示财务', department: '财务部', title: '会计', email: 'finance@example.test', status: '在职', manager: '演示财务主管', leaveBalanceDays: 6, salaryCents: 1800000, idNumber: '仅人事可见' },
]

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

function addAudit(action: string, actor: Actor, detail: string, origin: 'human' | 'ai' | 'system' = 'human', agentSuggestionId?: string) {
  gapDAudit.unshift({ id: `gapd-audit-${Date.now()}`, action, origin, agentSuggestionId, actor: actor.name, at: new Date().toISOString(), detail })
}

export const gapDPermissionKeys = {
  employeeSalaryRead: 'employee.salary:read',
  employeeIdNumberRead: 'employee.id_number:read',
  payrollCalculate: 'payroll_run:calculate',
  payrollApprove: 'payroll_entry:approve',
  payslipReadOwn: 'salary_slip:read_own',
  payslipReadAll: 'salary_slip:read_all',
} as const

function permission(actor: Actor, permissionKey: string) {
  return effectivePermission(roleSubject(actor.role, actor.userId), permissionKey)
}

function hasScope(actor: Actor, permissionKey: string, scope: 'all' | 'self') {
  const result = permission(actor, permissionKey)

  return result.allowed && result.dataScopes.includes(scope)
}

function isOwnEmployee(employee: GapDEmployee, actor: Actor) {
  return Boolean(actor.userId) && employee.userId === actor.userId
}

function canReadEmployeeField(employee: GapDEmployee, actor: Actor, permissionKey: string) {
  return hasScope(actor, permissionKey, 'all') || (hasScope(actor, permissionKey, 'self') && isOwnEmployee(employee, actor))
}

function findEmployee(employeeId: string) {
  return gapDEmployees.find(employee => employee.id === employeeId)
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
    return gapDEmployees.map(row => {
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

export function updateGapDAutonomy(id: string, requested: AgentAutonomyLevel, actor: Actor) {
  const policy = gapDAutonomyPolicies.find(row => row.id === id)
  if (!policy)
    throw new Error('自治策略不存在')
  const result = validateAutonomyLevel(policy.action, requested, policy.hardMaxLevel)
  if (!result.ok)
    throw new Error(result.reason)
  policy.level = result.level
  addAudit('更新自主等级', actor, `${policy.action} → ${result.level}`)

  return policy
}

export function updateGapDAiMode(mode: 'normal' | 'degraded' | 'off', reason: string, actor: Actor) {
  addAudit('切换 AI 总开关', actor, `${mode}：${reason}`)

  return { mode, changedAt: new Date().toISOString(), changedBy: actor.name, reason }
}

export function saveGapDTool(input: Partial<GapDTool>, actor: Actor) {
  const tool: GapDTool = { id: input.id ?? `tool-${Date.now()}`, name: input.name ?? '自定义 HTTP 工具', kind: input.kind ?? 'http', sideEffect: 'none', enabled: false, readOnly: true, secretConfigured: Boolean(input.secretConfigured), frequencyLimit: input.frequencyLimit ?? 20, autonomyLevel: 'L1', roles: input.roles ?? ['admin'], endpoint: input.endpoint }
  const existing = gapDTools.findIndex(row => row.id === tool.id)
  if (existing >= 0)
    gapDTools[existing] = { ...gapDTools[existing], ...tool }
  else
    gapDTools.push(tool)
  addAudit('保存智能体工具', actor, `${tool.name} 默认停用、只读`)

  return tool
}

export function toggleGapDTool(id: string, enabled: boolean, actor: Actor) {
  const tool = gapDTools.find(row => row.id === id)
  if (!tool)
    throw new Error('工具不存在')
  tool.enabled = enabled
  addAudit(enabled ? '启用智能体工具' : '停用智能体工具', actor, `${tool.name}：${enabled ? '启用' : '停用'}`)

  return tool
}

export function ingestGapDInbox(fileName: string, actor: Actor) {
  const record: GapDRecord = { id: `inbox-${Date.now()}`, title: fileName, status: '待识别', owner: actor.name, detail: '文件已收件，等待确定性字段抽取', updatedAt: new Date().toISOString() }

  genericRows.G20 = [record, ...(genericRows.G20 ?? [])]
  addAudit('上传票据', actor, fileName)

  return record
}

export function importGapDMcpTool(serverId: string, actor: Actor) {
  const server = gapDMcpServers.find(row => row.id === serverId)
  if (!server)
    throw new Error('MCP 服务器不存在')
  for (const name of server.discoveredTools)
    saveGapDTool({ id: `mcp-${server.id}-${name}`, name, kind: 'mcp', roles: ['admin'] }, actor)
  server.imported = true
  addAudit('导入 MCP 工具', actor, `${server.name}：${server.discoveredTools.join('、')}`)

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
  if (!hasScope(actor, gapDPermissionKeys.payrollCalculate, 'all'))
    throw new Error('当前用户没有算薪权限')
  const rule = gapDPayrollRules[0]
  const month = Number(period.slice(5, 7)) || 1

  const payslips: GapDPayslip[] = gapDEmployees.filter(row => row.status !== '离职').map(employee => {
    const grossCents = employee.salaryCents ?? 0
    const base = Math.min(rule.baseMaxCents, Math.max(rule.baseMinCents, grossCents))
    const social = Math.round(base * (rule.pensionRate + rule.medicalRate + rule.unemploymentRate))
    const housing = Math.round(base * rule.housingFundRate)
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

export function listGapDAudit() {
  return gapDAudit
}
