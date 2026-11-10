import { fetchMyApprovals } from '@/api/approvals'
import { fetchMyDashboard, fetchMyTodos } from '@/api/dashboard'
import { canPermission, currentActor } from '@/api/mock-client'
import { fetchScopedContext, fetchScopedExpenses, fetchScopedOrders } from '@/api/scoped-reads'
import type { ScopedContext } from '@/api/scoped-reads'
import type { ScopedExpense, ScopedOrder } from '@/mocks/services/scoped-reads'
import type { ApprovalItem, DashboardPayload, TodoRow } from '@/types/domain'

export interface HomeApproval {
  id: string
  title: string
  summary: string
  submittedAt: string
  to: string
}

export interface HomePayload {
  actor: ReturnType<typeof currentActor>
  dashboard?: DashboardPayload
  tasks: TodoRow[]
  approvals: HomeApproval[]
  orders: ScopedOrder[]
  expenses: ScopedExpense[]
  scope?: ScopedContext
}

async function safely<T>(loader: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await loader()
  }
  catch {
    return fallback
  }
}

function toHomeApproval(item: ApprovalItem): HomeApproval {
  return {
    id: item.id,
    title: item.title,
    summary: item.summary,
    submittedAt: item.submittedAt,
    to: `/approvals/${item.id}`,
  }
}

/**
 * 首页只编排已有的权限 API。每个板块独立失败时会被隐藏，避免一个无权限接口阻塞整页。
 * 这里不读取员工档案等敏感接口，敏感字段由服务层裁剪后才允许进入页面。
 */
export async function fetchHome(): Promise<HomePayload> {
  const actor = currentActor()
  const reportReadable = canPermission('report:read')
  const approvalReadable = canPermission('approval:read')
  const orderReadable = canPermission('sales_order:read')
  const expenseReadable = canPermission('expense_claim:read')

  const [dashboard, tasks, approvals, orders, expenses, scope] = await Promise.all([
    reportReadable ? safely(() => fetchMyDashboard(), undefined) : Promise.resolve(undefined),
    safely(() => fetchMyTodos(), []),
    approvalReadable ? safely(() => fetchMyApprovals(), []) : Promise.resolve([]),
    orderReadable ? safely(() => fetchScopedOrders(), []) : Promise.resolve([]),
    expenseReadable ? safely(() => fetchScopedExpenses(), []) : Promise.resolve([]),
    safely(() => fetchScopedContext(), undefined),
  ])

  return {
    actor,
    dashboard,
    tasks,
    approvals: approvals.filter(item => item.status === 'pending').map(toHomeApproval),
    orders,
    expenses,
    scope,
  }
}
