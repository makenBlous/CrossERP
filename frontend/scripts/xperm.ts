/* eslint-disable @typescript-eslint/no-unused-vars, unused-imports/no-unused-imports, max-statements-per-line, antfu/if-newline, comma-spacing, @stylistic/ts/comma-spacing, lines-around-comment, padding-line-between-statements, prefer-template, prefer-const, @stylistic/ts/brace-style, indent, @stylistic/ts/indent */
// 独立权限实测（不是 Codex 写的）：页面默认拒绝 / 模板分工 / 旧 5 角色基线 / 拒绝优先 / 临时授权 / 服务层拦截 / 字段裁剪
import { readFileSync } from 'node:fs'
import { canRoleOpen, pageCatalog } from '@/config/pages'
import { computeEffectivePermissions, effectivePermission, fieldAccess, roleSubject } from '@/utils/permission-engine'
import { requireActorPermission } from '@/utils/service-permissions'

const out: string[] = []; let fail = 0
const ok = (c: boolean, m: string) => { out.push(`${c ? 'PASS' : 'FAIL'} ${m}`); if (!c) fail++ }
const T = ['owner_manager','operations_manager','store_operator','advertising','product_developer','purchaser','warehouse_logistics','customer_service','accountant','finance_manager','cashier','hr_admin','employee','department_manager','auditor_template','external_viewer'] as any[]
const OLD = ['admin','operator','finance','viewer','auditor'] as any[]
// 1 默认拒绝：每页都有 requiredPermissions
const noReq = pageCatalog.filter(p => !p.public && !(p.requiredPermissions?.length))
ok(noReq.length === 0, `所有非公开页面声明权限点（缺 ${noReq.length}）`)
// 2 旧 5 角色与基线逐页一致
const base = JSON.parse(readFileSync(process.env.TEMP + '/cx-pw/b0_base_pages.json', 'utf8').replace(/^\uFEFF/, '')) as any[]
let mism: string[] = []
for (const r of OLD) for (const b of base) { if (b.public || b.path === '/*') continue; const p = pageCatalog.find(x => x.path === b.path); if (!p) { mism.push(`missing ${b.path}`); continue } const exp = b.roles.includes(r); if (canRoleOpen(r, p) !== exp) mism.push(`${r} ${b.path} exp=${exp}`) }
ok(mism.length === 0, `旧 5 角色 × 旧页面与基线一致（差异 ${mism.length}）${mism.slice(0, 5).join('; ')}`)
// 3 模板分工：敏感页
const SENS: Record<string, string[]> = { '/admin/users': ['owner_manager'], '/admin/roles': ['owner_manager'], '/admin/permission-matrix': ['owner_manager'], '/finance/vouchers': ['owner_manager','accountant','finance_manager','auditor_template'], '/hr/payroll': ['owner_manager','hr_admin','finance_manager'], '/hr/employees': ['owner_manager','hr_admin','department_manager'] }
for (const [path, allowedHint] of Object.entries(SENS)) { const p = pageCatalog.find(x => x.path === path); if (!p) { ok(false, `页面不存在 ${path}`); continue } const who = T.filter(t => canRoleOpen(t, p)); out.push(`INFO ${path} 可开模板: ${who.join(',') || '无'}（参考预期: ${allowedHint.join(',')}）`) }
for (const t of ['employee','external_viewer','customer_service','warehouse_logistics','advertising']) for (const path of ['/admin/users','/admin/roles','/admin/permission-matrix','/finance/vouchers','/hr/payroll']) { const p = pageCatalog.find(x => x.path === path)!; ok(!canRoleOpen(t, p), `${t} 不能打开 ${path}`) }
ok(!canRoleOpen('hr_admin' as any, pageCatalog.find(x => x.path === '/finance/vouchers')!), 'hr_admin 不能打开财务凭证')
ok(!canRoleOpen('hr_admin' as any, pageCatalog.find(x => x.path === '/admin/permission-matrix')!), 'hr_admin 不能打开权限矩阵')
for (const t of T) { const n = pageCatalog.filter(p => !p.public && canRoleOpen(t, p)).length; out.push(`INFO ${t} 可开页面 ${n}`) }
// 4 拒绝优先 + 临时授权到期
const now = Date.parse('2026-11-10T00:00:00Z')
const subjDeny: any = { userId: 'u-x', roleIds: ['admin'], overrides: [{ id: 'o1', userId: 'u-x', permissionKey: 'journal_entry:create', effect: 'deny', reason: 'test' }] }
ok(effectivePermission(subjDeny, 'journal_entry:create', now).allowed === false, '显式拒绝优先于 admin 允许')
const subjTmp: any = { userId: 'u-y', roleIds: ['employee'], temporaryGrants: [{ id: 't1', userId: 'u-y', grantType: 'temporary', permissionKey: 'purchase_order:read', effect: 'allow', startsAt: '2026-11-01T00:00:00Z', expiresAt: '2026-11-08T00:00:00Z', reason: 'test' }] }
ok(effectivePermission(subjTmp, 'purchase_order:read', now).allowed === false, '临时授权到期后失效')
ok(effectivePermission(subjTmp, 'purchase_order:read', Date.parse('2026-11-05T00:00:00Z')).allowed === true, '临时授权有效期内生效')
// 5 服务层拦截（mock API 写操作）
const actor = (role: string) => ({ userId: `demo-${role}`, name: role, role, at: '2026-11-10T00:00:00Z' }) as any
for (const [role, key] of [['employee','journal_entry:create'],['external_viewer','journal_entry:submit'],['hr_admin','permission:write'],['customer_service','payment_entry:create'],['viewer','journal_entry:create']] as const) {
  let threw = false; try { requireActorPermission(actor(role), key) } catch { threw = true }
  ok(threw, `服务层拒绝 ${role} 执行 ${key}`)
}
let adminOk = true; try { requireActorPermission(actor('admin'), 'journal_entry:create') } catch { adminOk = false }
ok(adminOk, '服务层允许 admin 执行 journal_entry:create')
// 6 字段权限
for (const fk of ['salary', 'idCard', 'salaryDetail']) {
  for (const role of ['employee', 'finance', 'accountant', 'finance_manager', 'cashier', 'external_viewer', 'operator', 'viewer', 'auditor', 'store_operator', 'department_manager']) {
    const a = fieldAccess(roleSubject(role as any), fk); ok(a === 'hidden' || a === 'masked', `${role} 字段 ${fk} 不可见（实际 ${a}）`)
  }
  const hrA = fieldAccess(roleSubject('hr_admin' as any), fk); ok(hrA === 'visible' || hrA === 'readonly', `hr_admin 字段 ${fk} 可见（实际 ${hrA}）`)
}
out.push(`INFO 未登记字段 key 的默认结果: ${fieldAccess(roleSubject('employee' as any), 'unknownSensitiveField')}`)
for (const role of ['finance', 'operator', 'viewer', 'auditor']) for (const k of ['employee.salary:read', 'salary_slip:read_all', 'employee.id_number:read']) ok(!effectivePermission(roleSubject(role as any), k).allowed, `旧角色 ${role} 没有 ${k}`)
console.log(out.join('\n')); console.log(`== FAIL ${fail}`)
process.exit(fail ? 1 : 0)
