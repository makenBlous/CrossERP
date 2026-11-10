import { assertPermission, delay } from '@/api/mock-client'
import { dataScopesFor, shopsForSubject } from '@/mocks/services/gap-c'
import { listScopedEmployees, listScopedExpenses, listScopedOrders } from '@/mocks/services/scoped-reads'
import { effectivePermission, roleSubject } from '@/utils/permission-engine'
import { useSessionStore } from '@/stores/session'

export interface ScopedContext {
  userId: string
  dataScopes: {
    orders: string[]
    expenses: string[]
    employees: string[]
  }
  shopsForSubject: string[]
}

function subject() {
  const session = useSessionStore()

  return roleSubject(session.role, session.userId)
}

export async function fetchScopedOrders() {
  await delay()
  assertPermission('sales_order:read')

  return listScopedOrders(subject())
}

export async function fetchScopedExpenses() {
  await delay()
  assertPermission('expense_claim:read')

  return listScopedExpenses(subject())
}

export async function fetchScopedEmployees() {
  await delay()

  const current = subject()
  const readAll = effectivePermission(current, 'employee_record:read')

  if (readAll.deniedBy.length > 0 || (!readAll.allowed && !effectivePermission(current, 'employee_record:read_own').allowed))
    assertPermission('employee_record:read')

  return listScopedEmployees(current)
}

export async function fetchScopedContext(): Promise<ScopedContext> {
  await delay()

  const current = subject()

  return {
    userId: current.userId,
    dataScopes: {
      orders: dataScopesFor(current, 'sales_order:read'),
      expenses: dataScopesFor(current, 'expense_claim:read'),
      employees: dataScopesFor(current, 'employee_record:read'),
    },
    shopsForSubject: shopsForSubject(current),
  }
}
