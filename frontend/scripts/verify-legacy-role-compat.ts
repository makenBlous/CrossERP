/* 旧五角色兼容性回归：调用真实 API/service，禁止只检查菜单。 */
import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
import { canRoleOpen, findPageByPath } from '@/config/pages'
import { roleTemplates } from '@/config/permissions'
import { decideApproval } from '@/api/approvals'
import { changePassword, createAccountToken, fetchTokens, revokeAccountToken } from '@/api/account'
import { saveRoleVisibility } from '@/api/admin'
import { createGapAClaim, decideGapAClaim, submitGapAClaim } from '@/api/gap-a'
import { fetchAp, fetchCash, fetchClearing, submitVoucherApproval } from '@/api/finance'
import { approveLeave, approvePayroll, calculateGapDPayrollRun, publishPayslips, reviewPayroll } from '@/api/gap-d'
import { createGapCTemporaryGrant, fetchGapCMatrix, saveGapCDataScope, saveGapCMatrix } from '@/api/gap-c'
import { submitGapBAction } from '@/api/gap-b'
import { createKbDocument, decideKbReview, fetchKbReviews, submitKbDocument } from '@/api/gap-e'
import { approvePurchaseOrder, submitPurchaseOrder } from '@/api/workflows'
import { useSessionStore } from '@/stores/session'
import { database } from '@/api/mock-client'
import { computeEffectivePermissions, effectivePermission, roleSubject } from '@/utils/permission-engine'
import type { Role } from '@/types/domain'

const memoryStorage = () => {
  const values = new Map<string, string>()

  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, String(value)),
    removeItem: (key: string) => values.delete(key),
    clear: () => values.clear(),
    key: (index: number) => [...values.keys()][index] ?? null,
    get length() { return values.size },
  }
}

;(globalThis as any).sessionStorage = memoryStorage()
;(globalThis as any).localStorage = memoryStorage()
setActivePinia(createPinia())

const session = useSessionStore()
const oldRoles: Role[] = ['admin', 'operator', 'finance', 'viewer', 'auditor']
const templateRoles = roleTemplates.map(item => item.id as Role)
let failures = 0

function as(role: Role) {
  session.setRole(role)
}

function check(label: string, condition: boolean) {
  if (!condition)
    failures += 1
  console.log(`${condition ? 'PASS' : 'FAIL'} ${label}`)
}

async function allowed(label: string, call: () => Promise<unknown>) {
  try {
    await call()
    check(label, true)
  }
  catch (error) {
    check(`${label}（${error instanceof Error ? error.message : String(error)}）`, false)
  }
}

async function denied(label: string, call: () => Promise<unknown>) {
  try {
    await call()
    check(`${label}（意外放行）`, false)
  }
  catch {
    check(label, true)
  }
}

// 1. A/C/D 的新增权限点只补到旧主体；模板不从 legacyRole 继承。
const requiredLegacy: Record<Role, string[]> = {
  admin: ['expense_claim:approve_manager', 'expense_claim:approve_finance', 'leave_application:approve_manager', 'leave_application:approve_hr', 'salary_slip:review', 'payroll_run:calculate'],
  operator: ['agent_autonomy:write', 'agent_mode:write'],
  finance: ['budget:write', 'employee_advance:write', 'expense_claim:approve_finance', 'expense_claim_type:write', 'export_tax_rebate:write', 'vat_return:write', 'journal_entry:submit'],
  viewer: [],
  auditor: [],
}

for (const role of oldRoles) {
  for (const permission of requiredLegacy[role])
    check(`旧 ${role} 保留 ${permission}`, effectivePermission(roleSubject(role), permission).allowed)
}
for (const role of templateRoles) {
  const subject = roleSubject(role)

  check(`模板 ${role} 不继承旧 finance 的 journal_entry:submit`, role === 'finance_manager' ? !effectivePermission(subject, 'journal_entry:submit').allowed : true)

  const roleById = new Map(roleTemplates.map(item => [item.id, item]))
  const expected = new Map<string, 'allow' | 'deny'>()

  const collect = (id: string) => {
    const template = roleById.get(id)
    if (!template)
      return
    for (const parentId of template.parentIds)
      collect(parentId)
    for (const permission of template.permissions)
      expected.set(permission.permissionKey, permission.effect)
  }

  collect(role)

  const expectedAllowed = new Set([...expected.entries()].filter(([, effect]) => effect === 'allow').map(([key]) => key))
  const actualAllowed = new Set(computeEffectivePermissions(subject).filter(item => item.allowed).map(item => item.permissionKey))

  check(`模板 ${role} 有效权限严格等于模板定义`, expectedAllowed.size === actualAllowed.size && [...expectedAllowed].every(key => actualAllowed.has(key)))
}
check('department_manager 保留 D 部门主管请假一级审批', effectivePermission(roleSubject('department_manager'), 'leave_application:approve_manager').allowed)
check('finance_manager 遵守 D 工资条隐私，不具备 salary_slip:read', !effectivePermission(roleSubject('finance_manager'), 'salary_slip:read').allowed)

// 2. A：真实报销审批链、职责分离和自审。
as('admin')
await allowed('admin 真实调用报销主管级审批', () => decideGapAClaim('exp-001', 'manager', 'approved'))
as('finance')
await allowed('finance 真实调用报销财务级审批', () => decideGapAClaim('exp-001', 'finance', 'approved'))
as('admin')

const selfClaim = await createGapAClaim({ claimant: '演示管理员', department: '人事行政部', attachmentName: 'self.pdf', line: { category: '办公用品', description: '自审回归', amount: 100, currency: 'CNY' }, origin: 'human' })

await submitGapAClaim(selfClaim.id)
await denied('报销提交人不能审批自己的报销', () => decideGapAClaim(selfClaim.id, 'manager', 'approved'))

// 3. 批次 0/C：finance 提交凭证，admin 审批他人提交的凭证，提交人不能自审。
as('finance')

const voucherApproval = await submitVoucherApproval('vch-1')

await denied('凭证提交人不能自审', () => decideApproval(voucherApproval.id, 'approved'))
as('admin')
await allowed('admin 审批 finance 提交的凭证', () => decideApproval(voucherApproval.id, 'approved'))

// 4. B、C、D、E 各取一个真实写入口。
as('admin')
await allowed('admin 执行 B 渠道/采购写入', () => submitGapBAction('S09', 'create-rfq', { subject: '兼容回归询价', supplierCount: 2, amount: '100' }))

const purchaseId = database().db.purchaseOrders[10]?.id

assert(purchaseId)
as('owner_manager')
await allowed('老板模板提交采购单', () => submitPurchaseOrder(purchaseId))
await denied('采购提交人不能自审', () => approvePurchaseOrder(purchaseId))
as('admin')

const matrix = await fetchGapCMatrix()

await allowed('admin 保存 C 权限矩阵', () => saveGapCMatrix(matrix.slice(0, 1)))

const payroll = await calculateGapDPayrollRun('2026-12')

await allowed('admin 执行 D 薪资复核', () => reviewPayroll(payroll.id, '兼容性回归复核'))
await denied('工资复核人不能自审', () => approvePayroll(payroll.id))
as('finance')
await allowed('finance 执行 D 薪资审批', () => approvePayroll(payroll.id))
as('admin')
await allowed('admin 执行 D 工资条发布', () => publishPayslips(payroll.id))
await allowed('admin 执行 D 请假逐级审批第一步', () => approveLeave('leave-001'))
await allowed('admin 执行 D 请假逐级审批第二步', () => approveLeave('leave-001'))
as('operator')

const document = await createKbDocument({ title: '兼容性回归文档', content: '回归', kind: 'policy', spaceId: 'space-company', tags: [], expiresOn: null })

await submitKbDocument(document.id)
as('admin')

const review = (await fetchKbReviews()).find(item => item.targetId === document.id)

assert(review)
await allowed('admin 审批 E 知识库文档', () => decideKbReview(review.id, 'approve'))

// 5. 旧角色页面与真实 finance API 仍与历史入口一致；finance 页面脚本会补齐逐页接口矩阵。
for (const role of oldRoles) {
  for (const [path, expected] of [['/finance/ap', ['admin', 'finance', 'viewer'].includes(role)], ['/finance/cash', ['admin', 'finance'].includes(role)], ['/finance/clearing', ['admin', 'finance'].includes(role)]] as const) {
    const page = findPageByPath(path)

    assert(page)
    check(`旧 ${role} 页面 ${path} 与基准一致`, canRoleOpen(role, page) === expected)
  }
}
as('viewer')
await allowed('viewer 读取应付（历史合法入口）', () => fetchAp())
as('operator')
await denied('operator 读取应付仍被拒绝', () => fetchAp())
await denied('operator 读取现金仍被拒绝', () => fetchCash())
await denied('operator 读取清算仍被拒绝', () => fetchClearing())
as('auditor')
await denied('auditor 读取应付仍被拒绝', () => fetchAp())

// 6. user:write 只作用于本人账号和本人 Token；不能借此管理他人。
as('external_viewer')

const ownTokens = await fetchTokens()

check('external_viewer 只能列出自己的 Token', ownTokens.every(token => token.ownerUserId === 'demo-external-viewer'))

const ownToken = await createAccountToken('兼容回归本人 Token')

check('新 Token 记录稳定 ownerUserId', ownToken.token.ownerUserId === 'demo-external-viewer')
await allowed('本人可以撤销自己的 Token', () => revokeAccountToken(ownToken.token.id))

const db = database().db
const auditBefore = db.audit.length

as('admin')

const adminTokens = await fetchTokens()

check('admin 列出自己的 Token', adminTokens.length >= 1 && adminTokens.every(token => token.ownerUserId === 'demo-admin'))

const adminTokenId = adminTokens[0]?.id

assert(adminTokenId)
as('external_viewer')
await denied('不能撤销他人的 Token', () => revokeAccountToken(adminTokenId))
check('越权撤销没有副作用或审计', db.accountTokens?.find(token => token.id === adminTokenId)?.revoked === false && db.audit.length === auditBefore)

const overrideBefore = db.roleOverrides?.length ?? 0

await denied('user:write 不能修改角色权限范围', () => saveRoleVisibility('admin', [], []))
check('越权角色写没有副作用', (db.roleOverrides?.length ?? 0) === overrideBefore)
await denied('user:write 不能修改权限矩阵', () => saveGapCMatrix([]))
await denied('user:write 不能修改他人数据范围', () => saveGapCDataScope('owner_manager-scope', 'all'))
await denied('user:write 不能创建用户例外授权', () => createGapCTemporaryGrant({ userId: 'demo-admin', permissionKey: 'report:read', effect: 'allow', startsAt: '2026-11-10T00:00:00Z', expiresAt: '2026-11-11T00:00:00Z', reason: '越权回归' }))

const passwordAuditBefore = db.audit.length

await allowed('本人可以修改自己的密码', () => changePassword())

const passwordAudit = db.audit[db.audit.length - 1]

check('修改密码审计记录 actorId', db.audit.length === passwordAuditBefore + 1 && passwordAudit?.actorId === 'demo-external-viewer')

console.log(`== FAIL ${failures}`)
process.exit(failures ? 1 : 0)
