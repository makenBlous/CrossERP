import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

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
