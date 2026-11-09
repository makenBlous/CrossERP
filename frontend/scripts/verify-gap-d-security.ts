import assert from 'node:assert/strict'

import { approveGapDLeave, gapDEmployees, gapDPayrollRuns, getGapDPayrollRun, listGapDRecords, saveGapDTool, submitGapDLeave } from '../src/mocks/services/gap-d'
import type { Actor } from '../src/types/entities'
import type { GapDPayrollRun, GapDPayslip } from '../src/types/gap-d'

const at = '2026-11-10T08:00:00+08:00'

const finance: Actor = { userId: 'demo-finance', name: '演示财务', role: 'finance', at }
const admin: Actor = { userId: 'demo-admin', name: '演示管理员', role: 'admin', at }
const employee: Actor = { userId: 'demo-employee', name: '演示普通员工', role: 'employee', at }
const hr: Actor = { userId: 'demo-hr-admin', name: '演示人事行政', role: 'hr_admin', at }
const noPermission: Actor = { userId: 'demo-external-viewer', name: '演示外部顾问', role: 'external_viewer', at }
const otherEmployee: Actor = { userId: 'demo-other-employee', name: '演示其他员工', role: 'employee', at }
const opsManager: Actor = { userId: 'demo-ops-manager', name: '演示运营主管', role: 'department_manager', at }
const financeManager: Actor = { userId: 'demo-fin-manager', name: '演示财务主管', role: 'department_manager', at }

const payslips: GapDPayslip[] = gapDEmployees.map((item, index) => ({
  id: `verify-payslip-${item.id}`,
  employeeId: item.id,
  employeeUserId: item.userId,
  employeeName: item.name,
  period: '2026-11',
  grossCents: 1000000 + index,
  socialPersonalCents: 1000,
  housingFundPersonalCents: 1000,
  taxableCumulativeCents: 998000,
  taxCents: 0,
  netCents: 998000,
  ruleVersion: 'verify',
  status: '待复核',
}))

const run: GapDPayrollRun = {
  id: 'payroll-verify-security',
  period: '2026-11',
  status: '待复核',
  employeeCount: payslips.length,
  payslips,
  createdAt: at,
}

gapDPayrollRuns.push(run)

let failures = 0

function check(label: string, assertion: () => void, dependency = false) {
  try {
    assertion()
    console.log(`[通过] ${label}`)
  }
  catch (error) {
    failures += 1

    const detail = error instanceof Error ? error.message : String(error)
    const suffix = dependency ? '（依赖批次 C 的权限契约）' : ''

    console.error(`[失败] ${label}${suffix}: ${detail}`)
  }
}

check('财务员工档案不返回 salaryCents 或 idNumber', () => {
  const records = listGapDRecords('HR02', finance)

  assert(records.every(record => !Object.prototype.hasOwnProperty.call(record, 'salaryCents')))
  assert(records.every(record => !Object.prototype.hasOwnProperty.call(record, 'idNumber')))
})

check('普通员工工资条只返回 userId 绑定的本人', () => {
  const records = listGapDRecords('HR12', employee)

  assert.equal(records.length, 1)
  assert.equal(records[0]?.id, 'verify-payslip-demo-employee')
}, true)

check('人事可以看到员工档案薪资字段和证件号', () => {
  const employeeRecord = listGapDRecords('HR02', hr).find(record => record.userId === 'demo-employee')

  assert(employeeRecord)
  assert.equal(employeeRecord.salaryCents, 1200000)
  assert.equal(employeeRecord.idNumber, '仅人事可见')
}, true)

check('无权限用户调用工资接口得到空/拒绝', () => {
  assert.deepEqual(listGapDRecords('HR12', noPermission), [])
  assert.equal(getGapDPayrollRun(run.id, noPermission), null)
})

check('AI 代普通员工查询看不到别人的工资', () => {
  const visible = listGapDRecords('HR12', employee)

  assert(visible.every(record => record.id === 'verify-payslip-demo-employee'))
})

check('其他员工按 userId 只看到本人档案和本人工资条', () => {
  const employeeRecords = listGapDRecords('HR02', otherEmployee)
  const payslipRecords = listGapDRecords('HR12', otherEmployee)

  assert(employeeRecords.length >= 1)
  assert(employeeRecords.every(record => record.userId === 'demo-other-employee'))
  assert(payslipRecords.length === 1)
  assert.equal(payslipRecords[0]?.id, 'verify-payslip-demo-other-employee')
})

check('AI 只能起草，不能直接提交请假或审批', () => {
  assert.throws(() => submitGapDLeave({ startDate: '2026-12-01', endDate: '2026-12-01', reason: 'AI 草稿' }, employee, 'ai'), /AI 只能起草/)
  assert.throws(() => approveGapDLeave('leave-001', employee, 'ai'), /AI 只能起草/)
})

check('财务不能跳过主管审批请假', () => {
  assert.throws(() => approveGapDLeave('leave-001', finance), /不能跳过主管/)
})

check('跨部门主管不能审批运营部请假', () => {
  assert.throws(() => approveGapDLeave('leave-001', financeManager), /范围|部门/)
})

check('运营部主管可以按部门范围一审请假', () => {
  assert.equal(approveGapDLeave('leave-001', opsManager).status, '待人事审批')
})

check('工具写接口默认停用只读且需要有效权限', () => {
  const tool = saveGapDTool({ name: 'verify-http', kind: 'http' }, admin)

  assert.equal(tool.enabled, false)
  assert.equal(tool.readOnly, true)
  assert.throws(() => saveGapDTool({ name: 'verify-http-no-perm', kind: 'http' }, otherEmployee), /没有权限/)
})

console.log(`校验结束：${failures === 0 ? '全部通过' : `${failures} 项失败`}`)

if (failures > 0)
  process.exitCode = 1
