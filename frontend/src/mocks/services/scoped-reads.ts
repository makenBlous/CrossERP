import { projectGapCField, scopeAllows } from '@/mocks/services/gap-c'
import type { PermissionSubject } from '@/types/foundation'
import { effectivePermission } from '@/utils/permission-engine'

export interface ScopedOrder {
  id: string
  orderNo: string
  ownerId: string
  department: string
  total: number
  currency: 'CNY'
}

export interface ScopedExpense {
  id: string
  title: string
  ownerId: string
  department: string
  amount: number
  currency: 'CNY'
}

export interface ScopedEmployee {
  id: string
  name: string
  ownerId: string
  department: string
  salary: number
  idCard: string
  bankAccount: string
}

const orders: ScopedOrder[] = [
  { id: 'scoped-order-001', orderNo: 'DE-1001', ownerId: 'demo-operator', department: '运营部', total: 4200, currency: 'CNY' },
  { id: 'scoped-order-002', orderNo: 'FIN-1002', ownerId: 'demo-finance', department: '财务部', total: 8000, currency: 'CNY' },
]

const expenses: ScopedExpense[] = [
  { id: 'scoped-expense-001', title: '客户拜访住宿', ownerId: 'demo-employee', department: '运营部', amount: 2800, currency: 'CNY' },
  { id: 'scoped-expense-002', title: '财务培训', ownerId: 'demo-finance', department: '财务部', amount: 1800, currency: 'CNY' },
]

const employees: ScopedEmployee[] = [
  { id: 'scoped-employee-001', name: '演示员工', ownerId: 'demo-employee', department: '运营部', salary: 1200000, idCard: '110101199001010011', bankAccount: '6222000000000011' },
  { id: 'scoped-employee-002', name: '演示财务', ownerId: 'demo-finance', department: '财务部', salary: 1800000, idCard: '110101198801010022', bankAccount: '6222000000000022' },
]

function inScope(subject: PermissionSubject, permissionKey: string, ownerId: string, department: string) {
  return scopeAllows(subject, permissionKey, ownerId, department)
}

export function listScopedOrders(subject: PermissionSubject): ScopedOrder[] {
  return orders.filter(item => inScope(subject, 'sales_order:read', item.ownerId, item.department))
}

export function listScopedExpenses(subject: PermissionSubject): ScopedExpense[] {
  return expenses.filter(item => inScope(subject, 'expense_claim:read', item.ownerId, item.department))
}

export function listScopedEmployees(subject: PermissionSubject): Array<Partial<ScopedEmployee>> {
  const readAll = effectivePermission(subject, 'employee_record:read')
  if (readAll.deniedBy.length > 0)
    return []
  const permissionKey = readAll.allowed ? 'employee_record:read' : 'employee_record:read_own'

  return employees
    .filter(item => inScope(subject, permissionKey, item.ownerId, item.department))
    .map(item => projectGapCField(subject, { ...item } as Record<string, unknown>) as Partial<ScopedEmployee>)
}
