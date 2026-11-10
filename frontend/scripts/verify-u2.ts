import { existsSync, readFileSync } from 'node:fs'
import { strict as assert } from 'node:assert'
import { resolve } from 'node:path'
import { createPinia, setActivePinia } from 'pinia'
import { fetchMyApprovals } from '@/api/approvals'
import { fetchMyDashboard, fetchMyTodos } from '@/api/dashboard'
import { useMockDbStore } from '@/stores/mockdb'
import { useSessionStore } from '@/stores/session'
import { projectMyApprovals, projectMyTodos, submitterId } from '@/mocks/services/home'
import { effectivePermission, roleSubject } from '@/utils/permission-engine'
import { scopeAllows } from '@/mocks/services/gap-c'

const root = resolve(import.meta.dirname, '..')

function read(relativePath: string) {
  const file = resolve(root, relativePath)
  if (!existsSync(file))
    throw new Error(`缺少 U2 文件：${relativePath}`)

  return readFileSync(file, 'utf8')
}

const home = read('src/pages/dashboard/index.vue')
const api = read('src/api/home.ts')
const tour = read('src/components/tour/useOnboardingTour.ts')

const assertions: Array<[string, boolean]> = [
  ['首页有新人引导入口', /新人引导|重新开始引导/.test(home)],
  ['首页使用个人首页聚合 API', /fetchHome/.test(home)],
  ['首页展示待办与提醒', /待办|提醒/.test(home)],
  ['首页展示常用入口', /常用入口/.test(home)],
  ['聚合 API 读取当前 actor', /useSessionStore|currentActor/.test(api)],
  ['聚合 API 只通过现有 API 取数', /fetchDashboard|fetchTodos|fetchApprovals|fetchScopedOrders|fetchScopedExpenses/.test(api)],
  ['聚合 API 不读取工资字段', !/salary|工资|payslip/i.test(api)],
  ['引导使用 Shepherd 遮罩', /Shepherd|useModalOverlay/.test(tour)],
  ['引导支持跨页面路由', /router\.push|dashboard\/todos/.test(tour)],
  ['引导按 DOM 目标自动跳过', /querySelector|selector/.test(tour)],
  ['引导支持上一步、下一步、跳过', /上一步|下一步|跳过/.test(tour)],
]

const failures = assertions.filter(([, passed]) => !passed).map(([name]) => name)

if (failures.length) {
  console.error(`U2 静态检查失败（${failures.length} 项）：`)
  for (const failure of failures)
    console.error(`- ${failure}`)
  process.exit(1)
}

console.log(`U2 静态检查通过（${assertions.length} 项）`)

setActivePinia(createPinia())

const session = useSessionStore()
const database = useMockDbStore()
const roles = ['employee', 'customer_service', 'store_operator', 'department_manager', 'admin'] as const

for (const role of roles) {
  session.setRole(role)

  const subject = roleSubject(role, session.userId)
  const expectedTodos = projectMyTodos(database.db, subject, session.userId, session.displayName)
  const expectedApprovals = projectMyApprovals(database.db, subject, session.userId, session.displayName)
  const [todos, approvals] = await Promise.all([fetchMyTodos(), fetchMyApprovals()])

  assert.deepEqual(todos.map(item => item.id), expectedTodos.map(item => item.id), `${role} 待办必须使用服务层裁剪结果`)
  assert.deepEqual(approvals.map(item => item.id), expectedApprovals.map(item => item.id), `${role} 审批必须使用服务层裁剪结果`)

  for (const item of todos) {
    if (item.id.startsWith('po-')) {
      const order = database.db.purchaseOrders.find(row => `po-${row.id}` === item.id)

      assert.ok(order && (order.submittedById === session.userId || order.createdBy === session.displayName), `${role} 待办必须是本人负责或处理`)
    }
    else if (item.id.startsWith('ap-')) {
      const approval = database.db.approvals.find(row => `ap-${row.id}` === item.id)

      assert.ok(approval?.status === 'pending', `${role} 审批待办必须保持待处理状态`)

      const ownerId = approval ? submitterId(approval.submitter) : undefined
      const own = approval?.submitter === session.displayName || ownerId === session.userId
      const legal = Boolean(approval && ownerId && effectivePermission(subject, 'approval:approve').allowed && scopeAllows(subject, 'approval:approve', ownerId, undefined, approval.storeId ?? undefined))

      assert.equal(Boolean(own || legal), true, `${role} 审批待办必须是本人发起或合法审批范围`)
    }
  }

  for (const item of approvals) {
    const ownerId = submitterId(item.submitter)
    const own = item.submitter === session.displayName || ownerId === session.userId
    const legal = Boolean(ownerId && effectivePermission(subject, 'approval:approve').allowed && scopeAllows(subject, 'approval:approve', ownerId, undefined, database.db.approvals.find(row => row.id === item.id)?.storeId ?? undefined))

    assert.equal(item.status, 'pending', `${role} 我的审批必须是待审批单据`)
    assert.equal(Boolean(own || legal), true, `${role} 我的审批必须是本人发起或合法审批人可处理`)
  }

  const fixture = JSON.parse(JSON.stringify(database.db)) as typeof database.db

  fixture.purchaseOrders.push({
    ...fixture.purchaseOrders[0]!,
    id: `po-negative-${role}`,
    no: `PO-NEGATIVE-${role}`,
    status: 'submitted',
    submittedById: 'unknown-user',
    createdBy: '其他用户',
  })
  fixture.approvals.push({
    ...fixture.approvals[0]!,
    id: `apr-negative-${role}`,
    submitter: '其他用户',
    storeId: 'unknown-store',
    status: 'pending',
  })

  const negativeTodos = projectMyTodos(fixture, subject, session.userId, session.displayName)
  const negativeApprovals = projectMyApprovals(fixture, subject, session.userId, session.displayName)

  assert.equal(negativeTodos.some(item => item.id === `po-po-negative-${role}`), false, `${role} 不得返回其他用户待办`)
  assert.equal(negativeApprovals.some(item => item.id === `ap-apr-negative-${role}`), false, `${role} 不得返回其他用户审批`)

  const dashboard = await fetchMyDashboard()
  if (dashboard) {
    const allowedStoreIds = new Set(database.db.stores
      .filter(store => scopeAllows(subject, 'report:read', undefined, undefined, store.id))
      .map(store => store.id))

    assert.equal(dashboard.stores.every(store => allowedStoreIds.has(store.storeId)), true, `${role} KPI 不得越过允许店铺范围`)
    if (!allowedStoreIds.size)
      assert.equal(dashboard.stores.length, 0, `${role} 没有允许店铺时 KPI 必须为空`)
  }
}

session.setRole('employee')
assert.deepEqual(await fetchMyDashboard(), undefined, '没有 report:read 的角色不得获得 KPI')

console.log('U2 运行时范围检查通过（5 个角色 + 负例 + KPI 拒绝）')
