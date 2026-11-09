import assert from 'node:assert/strict'

import { gapDEmployees, gapDPayrollRuns, getGapDPayrollRun, listGapDRecords } from '../src/mocks/services/gap-d'
import type { Actor } from '../src/types/entities'
import type { GapDPayrollRun, GapDPayslip } from '../src/types/gap-d'

const at = '2026-11-10T08:00:00+08:00'

const finance: Actor = { userId: 'demo-finance', name: '演示财务', role: 'finance', at }
const employee: Actor = { userId: 'demo-employee', name: '演示普通员工', role: 'employee', at }
const hr: Actor = { userId: 'demo-hr-admin', name: '演示人事行政', role: 'hr_admin', at }
const noPermission: Actor = { userId: 'demo-external-viewer', name: '演示外部顾问', role: 'external_viewer', at }

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

console.log(`校验结束：${failures === 0 ? '全部通过' : `${failures} 项失败`}`)

if (failures > 0)
  process.exitCode = 1
