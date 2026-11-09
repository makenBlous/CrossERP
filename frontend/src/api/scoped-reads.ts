import { assertPermission, delay } from '@/api/mock-client'
import { listScopedEmployees, listScopedExpenses, listScopedOrders } from '@/mocks/services/scoped-reads'
import { effectivePermission, roleSubject } from '@/utils/permission-engine'
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

  const current = subject()
  const readAll = effectivePermission(current, 'employee_record:read')

  if (readAll.deniedBy.length > 0 || (!readAll.allowed && !effectivePermission(current, 'employee_record:read_own').allowed))
    assertPermission('employee_record:read')

  return listScopedEmployees(current)
}
