import { assertPermission, delay } from '@/api/mock-client'
import { listScopedEmployees, listScopedExpenses, listScopedOrders } from '@/mocks/services/scoped-reads'
import { roleSubject } from '@/utils/permission-engine'
import { useSessionStore } from '@/stores/session'

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
  assertPermission('employee_record:read')

  return listScopedEmployees(subject())
}
