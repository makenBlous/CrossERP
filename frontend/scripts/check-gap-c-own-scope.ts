import { strict as assert } from 'node:assert'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { createPinia, setActivePinia } from 'pinia'
import { fetchScopedEmployees, fetchScopedExpenses, fetchScopedOrders } from '@/api/scoped-reads'
import { canRoleOpen, pageCatalog } from '@/config/pages'
import { listScopedEmployees, listScopedExpenses, listScopedOrders } from '@/mocks/services/scoped-reads'
import { demoIdentities, useSessionStore } from '@/stores/session'
import { effectivePermission, roleSubject } from '@/utils/permission-engine'
import type { Role } from '@/types/domain'

const apiSource = readFileSync(resolve('src/api/scoped-reads.ts'), 'utf8')
const pageSource = readFileSync(resolve('src/pages/me/data-scope.vue'), 'utf8')

for (const functionName of ['fetchScopedOrders', 'fetchScopedExpenses', 'fetchScopedEmployees', 'fetchScopedContext']) {
  assert.match(apiSource, new RegExp(`export async function ${functionName}\\(\\s*\\)`), `${functionName} 必须是零参数当前主体 API`)
  assert.match(pageSource, new RegExp(`${functionName}\\(\\s*\\)`), `当前主体页面必须调用 ${functionName}()`)
}

assert.doesNotMatch(pageSource, /defineProps|useRoute|route\.query|query\./, '当前主体页面不得接受主体参数或读取 query')
assert.match(pageSource, /ScopedDataPreview/, '当前主体页面必须复用范围预览组件')
assert.match(readFileSync(resolve('src/components/biz/ScopedDataPreview.vue'), 'utf8'), /scope-preview-orders/)

const ownScopePage = pageCatalog.find(page => page.path === '/me/data-scope')

assert.ok(ownScopePage, '必须登记我的数据范围页面')

for (const role of Object.keys(demoIdentities) as Role[])
  assert.equal(canRoleOpen(role, ownScopePage), true, `${role} 必须能打开我的数据范围页面`)

setActivePinia(createPinia())

const session = useSessionStore()

interface ScopedResult {
  orders: Awaited<ReturnType<typeof fetchScopedOrders>>
  expenses: Awaited<ReturnType<typeof fetchScopedExpenses>>
  employees: Awaited<ReturnType<typeof fetchScopedEmployees>>
}

async function readAsCurrentSubject<T>(role: Role, id: string, read: () => Promise<T>): Promise<T> {
  session.setRole(role)

  return read()
}

function employeeReadAllowed(role: Role, id: string) {
  const subject = roleSubject(role, id)
  const readAll = effectivePermission(subject, 'employee_record:read')

  return readAll.deniedBy.length === 0 && (readAll.allowed || effectivePermission(subject, 'employee_record:read_own').allowed)
}

async function expectScopedReads(role: Role, id: string, admin: ScopedResult) {
  const subject = roleSubject(role, id)
  const orderAllowed = effectivePermission(subject, 'sales_order:read').allowed
  const expenseAllowed = effectivePermission(subject, 'expense_claim:read').allowed
  const employeeAllowed = employeeReadAllowed(role, id)

  if (orderAllowed)
    assert.deepEqual(await readAsCurrentSubject(role, id, fetchScopedOrders), listScopedOrders(subject), `${role} 订单范围不一致`)
  else
    await assert.rejects(() => readAsCurrentSubject(role, id, fetchScopedOrders), /没有权限|无权读取/)

  if (expenseAllowed)
    assert.deepEqual(await readAsCurrentSubject(role, id, fetchScopedExpenses), listScopedExpenses(subject), `${role} 报销范围不一致`)
  else
    await assert.rejects(() => readAsCurrentSubject(role, id, fetchScopedExpenses), /没有权限|无权读取/)

  if (employeeAllowed)
    assert.deepEqual(await readAsCurrentSubject(role, id, fetchScopedEmployees), listScopedEmployees(subject), `${role} 员工范围不一致`)
  else
    await assert.rejects(() => readAsCurrentSubject(role, id, fetchScopedEmployees), /没有权限|无权读取/)

  const current: ScopedResult = {
    orders: orderAllowed ? await readAsCurrentSubject(role, id, fetchScopedOrders) : [],
    expenses: expenseAllowed ? await readAsCurrentSubject(role, id, fetchScopedExpenses) : [],
    employees: employeeAllowed ? await readAsCurrentSubject(role, id, fetchScopedEmployees) : [],
  }

  for (const [key, rows] of Object.entries(current)) {
    const adminIds = new Set(admin[key as keyof ScopedResult].map(item => item.id))

    assert.ok(rows.every(item => adminIds.has(item.id)), `${role} ${key} 结果超出 admin 范围`)
  }
}

session.setRole('admin')

const admin = {
  orders: await fetchScopedOrders(),
  expenses: await fetchScopedExpenses(),
  employees: await fetchScopedEmployees(),
}

for (const [role, identity] of Object.entries(demoIdentities) as Array<[Role, { id: string }]>)
  await expectScopedReads(role, identity.id, admin)

console.log('gap-c own-scope checks passed')
