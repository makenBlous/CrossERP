import { strict as assert } from 'node:assert'
import { listScopedEmployees, listScopedExpenses, listScopedOrders } from '@/mocks/services/scoped-reads'
import { roleSubject } from '@/utils/permission-engine'

const departmentManager = listScopedEmployees(roleSubject('department_manager', 'demo-department-manager'))

assert.deepEqual(departmentManager.map(item => item.department), ['运营部'])

const employee = listScopedExpenses(roleSubject('employee', 'demo-employee'))

assert.deepEqual(employee.map(item => item.ownerId), ['demo-employee'])

const employeeRecord = listScopedEmployees(roleSubject('employee', 'demo-employee'))

assert.deepEqual(employeeRecord.map(item => item.ownerId), ['demo-employee'])
assert.equal('salary' in employeeRecord[0]!, false)

assert.deepEqual(listScopedOrders(roleSubject('external_viewer', 'demo-external-viewer')), [])
assert.deepEqual(listScopedEmployees(roleSubject('external_viewer', 'demo-external-viewer')), [])

console.log('gap-c scoped mock reads passed')
