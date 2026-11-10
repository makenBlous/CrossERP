import { strict as assert } from 'node:assert'
import { readFileSync } from 'node:fs'
import { canRoleOpen, findPageByPath, pageCatalog } from '@/config/pages'
import { gapCReadHelpers } from '@/mocks/services/gap-c'
import { computeEffectivePermissions, effectivePermission, narrowAiPermissions, roleSubject } from '@/utils/permission-engine'
import type { Role } from '@/types/domain'

const now = Date.parse('2026-11-10T00:00:00.000Z')

// 新模板只使用自身权限，不能因为 legacyRoleMap 获得管理员权限。
assert.equal(effectivePermission(roleSubject('hr_admin'), 'permission:write', now).allowed, false)
assert.equal(effectivePermission(roleSubject('employee'), 'salary_slip:read', now).allowed, false)
assert.equal(effectivePermission(roleSubject('admin'), 'permission:write', now).allowed, true)

const oldRoles: Role[] = ['admin', 'operator', 'finance', 'viewer', 'auditor']

const templates: Role[] = [
  'owner_manager',
  'operations_manager',
  'store_operator',
  'advertising',
  'product_developer',
  'purchaser',
  'warehouse_logistics',
  'customer_service',
  'accountant',
  'finance_manager',
  'cashier',
  'hr_admin',
  'employee',
  'department_manager',
  'auditor_template',
  'external_viewer',
]

const basePages = JSON.parse(readFileSync('C:/Users/cimi/AppData/Local/Temp/cx-pw/b0_base_pages.json', 'utf8')) as Array<{ path: string; roles: Role[] }>

assert.equal(pageCatalog.length, 228)
assert.equal(pageCatalog.filter(page => page.batch === undefined).length, 128)
assert.equal(pageCatalog.filter(page => page.batch !== undefined).length, 100)
assert.equal(new Set(pageCatalog.map(page => page.id)).size, pageCatalog.length, 'pageCatalog 的 id 必须唯一')
assert.equal(new Set(pageCatalog.map(page => page.path)).size, pageCatalog.length, 'pageCatalog 的 path 必须唯一')
assert.deepEqual(
  pageCatalog.filter(page => !page.public).filter(page => !page.requiredPermissions?.length),
  [],
  '每个非公开页面必须声明页面级权限点',
)

const importWizard = findPageByPath('/integrations/import-wizard')

assert.ok(importWizard, '必须登记 INT01 导入向导')

assert.equal(canRoleOpen('admin', importWizard), true, 'admin 必须能打开 INT01 导入向导')
assert.equal(canRoleOpen('operator', importWizard), true, 'operator 必须能打开 INT01 导入向导')
for (const role of ['finance', 'viewer', 'auditor'] as Role[])
  assert.equal(canRoleOpen(role, importWizard), false, `${role} 不得打开 INT01 导入向导`)

for (const role of oldRoles) {
  const actual = pageCatalog.filter(page => page.batch === undefined && !page.public && canRoleOpen(role, page)).map(page => ({ path: page.path, role }))
  const expected = basePages.filter(page => page.roles.includes(role)).map(page => ({ path: page.path, role }))

  assert.deepEqual(actual, expected, `${role} 的旧页面访问必须与基线一致`)
}

for (const role of templates) {
  assert.equal(canRoleOpen(role, pageCatalog.find(page => page.path === '/admin/users')!), role === 'owner_manager')
  assert.equal(canRoleOpen(role, pageCatalog.find(page => page.path === '/admin/roles')!), ['owner_manager', 'auditor_template'].includes(role))
  assert.equal(canRoleOpen(role, pageCatalog.find(page => page.path === '/admin/permission-matrix')!), ['owner_manager', 'auditor_template'].includes(role))
}
assert.equal(canRoleOpen('employee', pageCatalog.find(page => page.path === '/finance/vouchers')!), false)

const inherited = effectivePermission({ userId: 'u-1', roleIds: ['operations_manager'] }, 'sales_order:read', now)

assert.equal(inherited.allowed, true)
assert.ok(inherited.sources.some(source => source.includes('店铺运营')))

const denied = effectivePermission({
  userId: 'u-2',
  roleIds: ['store_operator'],
  overrides: [{ id: 'deny-export', userId: 'u-2', permissionKey: 'sales_order:export', effect: 'deny', reason: '职责限制' }],
}, 'sales_order:export', now)

assert.equal(denied.allowed, false)
assert.ok(denied.deniedBy.some(source => source.includes('职责限制')))

const union = effectivePermission({ userId: 'u-3', roleIds: ['store_operator', 'accountant'] }, 'journal_entry:read', now)

assert.equal(union.allowed, true)

const temporary = { id: 'grant-cost', userId: 'u-4', permissionKey: 'sku_cost:read', effect: 'allow' as const, reason: '盘点', grantType: 'temporary' as const, expiresAt: '2026-11-17T00:00:00.000Z' }

assert.equal(effectivePermission({ userId: 'u-4', roleIds: ['employee'], temporaryGrants: [temporary] }, 'sku_cost:read', now).allowed, true)
assert.equal(effectivePermission({ userId: 'u-4', roleIds: ['employee'], temporaryGrants: [temporary] }, 'sku_cost:read', Date.parse('2026-11-18T00:00:00.000Z')).allowed, false)

const employeeSubject = roleSubject('employee', 'demo-employee')

assert.equal(gapCReadHelpers.fieldAccess(employeeSubject, 'salary'), 'hidden')
assert.deepEqual(gapCReadHelpers.projectGapCField(employeeSubject, { salary: 1200000, title: '运营专员' }), { title: '运营专员' })
assert.equal(gapCReadHelpers.scopeAllows(employeeSubject, 'expense_claim:read', 'demo-employee', '运营部', 'shop-cn-01'), true)
assert.equal(gapCReadHelpers.scopeAllows(employeeSubject, 'expense_claim:read', 'demo-finance', '财务部', 'shop-us-01'), false)

const ai = narrowAiPermissions(computeEffectivePermissions(roleSubject('accountant'), now), ['journal_entry:read'])

assert.equal(ai.find(item => item.permissionKey === 'journal_entry:read')?.allowed, true)
assert.equal(ai.find(item => item.permissionKey === 'sales_order:read')?.allowed, false)

const accessSummary = [...oldRoles, ...templates].map(role => ({
  role,
  oldPages: pageCatalog.filter(page => page.batch === undefined && !page.public && canRoleOpen(role, page)).length,
  newPages: pageCatalog.filter(page => page.batch !== undefined && !page.public && canRoleOpen(role, page)).length,
}))

console.table(accessSummary)
console.log('gap-c permission checks passed')
