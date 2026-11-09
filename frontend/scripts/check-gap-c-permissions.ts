import { strict as assert } from 'node:assert'
import { computeEffectivePermissions, effectivePermission, narrowAiPermissions, roleSubject } from '@/utils/permission-engine'

const now = Date.parse('2026-11-10T00:00:00.000Z')

// 新模板只使用自身权限，不能因为 legacyRoleMap 获得管理员权限。
assert.equal(effectivePermission(roleSubject('hr_admin'), 'permission:write', now).allowed, false)
assert.equal(effectivePermission(roleSubject('employee'), 'salary_slip:read', now).allowed, false)
assert.equal(effectivePermission(roleSubject('admin'), 'permission:write', now).allowed, true)

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

const ai = narrowAiPermissions(computeEffectivePermissions(roleSubject('accountant'), now), ['journal_entry:read'])

assert.equal(ai.find(item => item.permissionKey === 'journal_entry:read')?.allowed, true)
assert.equal(ai.find(item => item.permissionKey === 'sales_order:read')?.allowed, false)

console.log('gap-c permission checks passed')
