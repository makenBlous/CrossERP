import { strict as assert } from 'node:assert'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { createPinia, setActivePinia } from 'pinia'
import { fetchHome } from '@/api/home'
import { fetchMyDashboard } from '@/api/dashboard'
import { fetchMyApprovals as fetchApprovals } from '@/api/approvals'
import { fetchScopedEmployees } from '@/api/scoped-reads'
import { buildNav } from '@/navigation/build-nav'
import { canRoleOpen, findPageByPath, pageCatalog } from '@/config/pages'
import { roleTemplates } from '@/config/permissions'
import { useMockDbStore } from '@/stores/mockdb'
import { useSessionStore } from '@/stores/session'
import { projectMyApprovals, projectMyTodos, submitterId } from '@/mocks/services/home'
import { listScopedEmployees, listScopedExpenses, listScopedOrders } from '@/mocks/services/scoped-reads'
import { gapCReadHelpers } from '@/mocks/services/gap-c'
import { effectivePermission, roleSubject } from '@/utils/permission-engine'
import type { Role } from '@/types/domain'

const root = resolve(import.meta.dirname, '..')
const read = (relativePath: string) => readFileSync(resolve(root, relativePath), 'utf8')
const pageSource = read('src/config/pages.ts')
const guardSource = read('src/plugins/1.router/guards.ts')
const routerSource = read('src/plugins/1.router/index.ts')
const dashboardSource = read('src/pages/dashboard/index.vue')
const tourSource = read('src/components/tour/useOnboardingTour.ts')

assert.match(pageSource, /authenticated\?: boolean/, '页面定义必须支持已登录用户标记')
assert.match(pageSource, /id: 'D01'[\s\S]*?authenticated: true/, 'D01 必须声明任何已登录用户可访问')
assert.match(guardSource, /authenticated/, '路由守卫必须处理已登录用户标记')
assert.match(routerSource, /const rootRedirect[\s\S]*?path: '\/', redirect: '\/dashboard'/, '根路由必须有显式 dashboard 重定向')
assert.doesNotMatch(dashboardSource, /setTimeout\(\(\) => start\(\)/, '新人引导不能在首页自动弹出')
assert.match(dashboardSource, /@click="restart"/, '首页必须保留手动重新开始引导按钮')
assert.doesNotMatch(tourSource, /onMounted/, '引导 composable 不应自行挂载自动启动')

const oldRoles: Role[] = ['admin', 'operator', 'finance', 'viewer', 'auditor']
const templateRoles = roleTemplates.map(item => item.id as Role)
const roles = [...oldRoles, ...templateRoles]

assert.equal(new Set(roles).size, 21, '首页访问检查必须覆盖 21 个角色')

/**
 * 原表 demoShopBindings（67e84fe）经允许的种子 ID 替换后的期望。
 * 店铺绑定应直接使用种子中的店铺 ID：amz-us、shopify、amz-de。
 * 未列出的用户期望为空。不要从当前绑定反推。
 * demo-store-operator 是原键 demo-store_operator 的身份对齐，店铺仍是原表的 1 店。
 */
const expectedShopsByUserId: Record<string, readonly string[]> = {
  'demo-admin': ['amz-us', 'shopify', 'amz-de'],
  'demo-finance': ['amz-us', 'shopify', 'amz-de'],
  'demo-auditor': ['amz-us', 'shopify', 'amz-de'],
  'demo-viewer': ['amz-us'],
  'demo-operator': ['amz-us'],
  'demo-external-viewer': ['amz-de'],
  'demo-store-operator': ['amz-us'],
}

const emptyMetricRoles = new Set<Role>(['operations_manager', 'advertising', 'customer_service'])

function navPaths(role: Role): string[] {
  const paths: string[] = []

  const walk = (items: unknown[]) => {
    for (const item of items) {
      if (!item || typeof item !== 'object')
        continue
      const record = item as { to?: { path?: string }; children?: unknown[] }
      if (record.to?.path)
        paths.push(record.to.path)
      if (record.children)
        walk(record.children)
    }
  }

  walk(buildNav(role) as unknown[])

  return paths
}

function hasSalary(value: unknown): boolean {
  if (!value || typeof value !== 'object')
    return false
  if (Array.isArray(value))
    return value.some(hasSalary)

  return Object.entries(value).some(([key, child]) => /salary|工资|payslip/i.test(key) || hasSalary(child))
}

setActivePinia(createPinia())

const session = useSessionStore()

session.isLoggedIn = true

const database = useMockDbStore()
const dashboardPage = findPageByPath('/dashboard')

assert.ok(dashboardPage, '必须登记 D01 首页')

for (const role of roles) {
  session.setRole(role)

  const subject = roleSubject(role, session.userId)
  const nav = navPaths(role)

  assert.equal(canRoleOpen(role, dashboardPage), true, `${role} 路由守卫必须放行首页`)
  assert.ok(nav.includes('/dashboard'), `${role} 菜单必须显示首页`)

  const expectedShops = [...(expectedShopsByUserId[session.userId] ?? [])]

  assert.deepEqual(gapCReadHelpers.shopsForSubject(subject), expectedShops, `${role} 允许店铺必须等于原表映射，不能由当前绑定反推`)

  const home = await fetchHome()
  const expectedTodos = projectMyTodos(database.db, subject, session.userId, session.displayName)
  const expectedApprovals = projectMyApprovals(database.db, subject, session.userId, session.displayName)

  assert.deepEqual(home.tasks.map(item => item.id), expectedTodos.map(item => item.id), `${role} 首页待办必须是本人/合法范围`)
  assert.deepEqual(home.approvals.map(item => item.id), expectedApprovals.map(item => item.id), `${role} 首页审批必须是服务层范围`)
  assert.equal(hasSalary(home), false, `${role} 首页响应不得包含工资字段`)

  const orderPermission = effectivePermission(subject, 'sales_order:read').allowed
  const expensePermission = effectivePermission(subject, 'expense_claim:read').allowed
  const employeePermission = effectivePermission(subject, 'employee_record:read').allowed || effectivePermission(subject, 'employee_record:read_own').allowed
  if (orderPermission)
    assert.deepEqual(home.orders, listScopedOrders(subject), `${role} 首页订单必须使用当前主体范围`)
  else
    assert.deepEqual(home.orders, [], `${role} 无订单权限时首页不得返回订单`)
  if (expensePermission)
    assert.deepEqual(home.expenses, listScopedExpenses(subject), `${role} 首页费用必须使用当前主体范围`)
  else
    assert.deepEqual(home.expenses, [], `${role} 无费用权限时首页不得返回费用`)
  if (employeePermission && role === 'employee')
    assert.equal(hasSalary(listScopedEmployees(subject)), false, `${role} 员工读取不得泄露工资字段`)
  if (role === 'employee') {
    assert.equal(hasSalary(await fetchScopedEmployees()), false, 'employee 不得看到他人工资')
    assert.ok(home.tasks.every(item => !item.title.includes('其他用户')), 'employee 不得看到他人待办')

    const otherApprovals = database.db.approvals.filter(item => {
      const ownerId = submitterId(item.submitter)

      return item.status === 'pending' && Boolean(ownerId) && ownerId !== session.userId && item.submitter !== session.displayName
    })

    assert.ok(otherApprovals.length > 0, '员工他人待办断言必须有真实正例，不能因为数据为空而跳过')
    for (const approval of otherApprovals)
      assert.equal(home.tasks.some(task => task.id === `ap-${approval.id}`), false, `employee 不得看到他人待办 ${approval.id}`)

    const fixture = JSON.parse(JSON.stringify(database.db)) as typeof database.db
    const seedApproval = fixture.approvals[0]

    assert.ok(seedApproval, '注入他人待办需要至少一条审批种子')
    fixture.approvals.push({
      ...seedApproval,
      id: 'apr-other-user-positive',
      title: '其他用户的待办报销',
      submitter: '演示运营',
      status: 'pending',
      storeId: 'amz-us',
    })
    assert.equal(fixture.approvals.some(item => item.id === 'apr-other-user-positive' && submitterId(item.submitter) !== session.userId), true, '他人待办正例必须存在于数据中')

    const projected = projectMyTodos(fixture, subject, session.userId, session.displayName)

    assert.equal(projected.some(item => item.id === 'ap-apr-other-user-positive'), false, 'employee 不得看到注入的他人待办')
  }

  const reportPermission = effectivePermission(subject, 'report:read').allowed
  const dashboard = await fetchMyDashboard()
  if (emptyMetricRoles.has(role)) {
    assert.deepEqual(expectedShops, [], `${role} 原表没有店铺绑定`)
    for (const payload of [home.dashboard, dashboard]) {
      if (!payload) {
        assert.equal(payload, undefined, `${role} 首页经营指标不可见`)
        continue
      }
      assert.equal(payload.stores.length, 0, `${role} 首页经营店铺必须为空`)
      assert.equal(payload.kpi.sales, 0, `${role} 首页销售额必须为空`)
      assert.equal(payload.kpi.netProfit, 0, `${role} 首页净利润必须为空`)
      assert.equal(payload.kpi.fees, 0, `${role} 首页费用必须为空`)
    }
  }
  if (!reportPermission) {
    assert.equal(dashboard, undefined, `${role} 没有 report:read 时不得获得经营指标`)
  }
  else if (dashboard) {
    const allowedStoreIds = new Set(database.db.stores.filter(store => gapCReadHelpers.scopeAllows(subject, 'report:read', undefined, undefined, store.id)).map(store => store.id))

    assert.ok(dashboard.stores.every(store => allowedStoreIds.has(store.storeId)), `${role} 经营指标不得越过店铺范围`)
    if (allowedStoreIds.size)
      assert.ok(dashboard.stores.some(store => allowedStoreIds.has(store.storeId)), `${role} 有合法店铺时经营总览不能为空`)
  }

  const rawApprovals = await fetchApprovals()

  assert.ok(rawApprovals.every(item => item.status === 'pending'), `${role} 首页审批接口只允许待审批事项`)
  assert.ok(rawApprovals.every(item => {
    const source = database.db.approvals.find(row => row.id === item.id)
    const ownerId = source ? submitterId(source.submitter) : undefined

    return Boolean(source && (ownerId === session.userId || (ownerId && effectivePermission(subject, 'approval:approve').allowed && gapCReadHelpers.scopeAllows(subject, 'approval:approve', ownerId, undefined, source.storeId ?? undefined))))
  }), `${role} 审批接口不得返回越权事项`)
}

session.setRole('employee')
assert.deepEqual(await fetchMyDashboard(), undefined, 'employee 没有 report:read 时不得获得经营指标')

session.setRole('admin')

const visibleWorkbench = pageCatalog.filter(item => item.showInMenu && item.group === 'workbench' && item.id !== 'D01' && canRoleOpen('admin', item))

assert.ok(visibleWorkbench.length > 0, '管理员必须能打开工作台内除首页外的页面，否则菜单豁免断言没有正例')

const openNav = navPaths('admin')

for (const page of visibleWorkbench)
  assert.ok(openNav.includes(page.path), `未隐藏时管理员应看到 ${page.id}`)

const savedOverrides = database.db.roleOverrides

database.db.roleOverrides = [{ role: 'admin', hiddenGroups: ['workbench'], hiddenPageIds: [] }]

const hiddenNav = navPaths('admin')

assert.ok(hiddenNav.includes('/dashboard'), '隐藏工作台分组时首页仍可见')
for (const page of visibleWorkbench)
  assert.equal(hiddenNav.includes(page.path), false, `隐藏工作台时不得显示 ${page.id}`)

database.db.roleOverrides = savedOverrides

console.log('home access checks passed (21 roles, scoped APIs, salary and report guards)')
