import assert from 'node:assert/strict'

import { approveGapDPayroll, calculateGapDPayroll, getGapDPayrollRun, listGapDRecords, publishGapDPayslips, reviewGapDPayroll } from '../src/mocks/services/gap-d'
import type { Actor } from '../src/types/entities'
import type { GapDPayrollRun, GapDPayslip } from '../src/types/gap-d'

const at = '2026-11-10T08:00:00+08:00'
const admin: Actor = { userId: 'demo-admin', name: '演示管理员', role: 'admin', at }
const employee: Actor = { userId: 'demo-employee', name: '演示普通员工', role: 'employee', at }
const otherEmployee: Actor = { userId: 'demo-other-employee', name: '演示其他员工', role: 'employee', at }
const hr: Actor = { userId: 'demo-hr-admin', name: '演示人事行政', role: 'hr_admin', at }
const finance: Actor = { userId: 'demo-fin-manager', name: '演示财务主管', role: 'finance_manager', at }
let failures = 0

function check(label: string, assertion: () => void) {
  try {
    assertion()
    console.log(`[通过] ${label}`)
  }
  catch (error) {
    const detail = error instanceof Error ? error.message : String(error)

    console.error(`[失败] ${label}: ${detail}`)
    failures += 1
  }
}

function assertNoOwnPayslip(runId: string, actor: Actor) {
  assert.deepEqual(listGapDRecords('HR12', actor), [])
  assert.equal(getGapDPayrollRun(runId, actor)?.payslips.length, 0)
}

function assertBackofficeCanRead(run: GapDPayrollRun, actor: Actor) {
  assert.equal(listGapDRecords('HR12', actor).length, run.employeeCount)
  assert.equal(getGapDPayrollRun(run.id, actor)?.payslips.length, run.employeeCount)
}

function assertSafeCents(payslip: GapDPayslip) {
  for (const value of [payslip.grossCents, payslip.socialPersonalCents, payslip.housingFundPersonalCents, payslip.taxableCumulativeCents, payslip.taxCents, payslip.netCents])
    assert(Number.isSafeInteger(value))
}

const payroll = calculateGapDPayroll('2026-12', admin)

for (const stage of ['算薪后', '复核后', '财务审批后'] as const) {
  if (stage === '复核后')
    reviewGapDPayroll(payroll.id, '发布前可见性回归检查', hr)
  if (stage === '财务审批后')
    approveGapDPayroll(payroll.id, finance)

  check(`${stage}员工看不到本人工资条`, () => assertNoOwnPayslip(payroll.id, employee))
  check(`${stage} HR 能看到全部工资条`, () => assertBackofficeCanRead(payroll, hr))
  check(`${stage} 财务能看到全部工资条`, () => assertBackofficeCanRead(payroll, finance))
}

publishGapDPayslips(payroll.id, hr)

check('发布后员工只看到本人且状态为已发布', () => {
  const records = listGapDRecords('HR12', employee)
  const detail = getGapDPayrollRun(payroll.id, employee)

  assert.equal(records.length, 1)
  assert.equal(records[0]?.id, 'payslip-2026-12-demo-employee')
  assert.equal(records[0]?.status, '已发布')
  assert.equal(detail?.payslips.length, 1)
  assert.equal(detail?.payslips[0]?.employeeUserId, employee.userId)
  assert.equal(detail?.payslips[0]?.status, '已发布')
})

check('发布后其他员工只看到自己的工资条', () => {
  const records = listGapDRecords('HR12', otherEmployee)
  const detail = getGapDPayrollRun(payroll.id, otherEmployee)

  assert.equal(records.length, 1)
  assert.equal(records[0]?.id, 'payslip-2026-12-demo-other-employee')
  assert.equal(detail?.payslips.length, 1)
  assert.equal(detail?.payslips[0]?.employeeUserId, otherEmployee.userId)
})

check('工资金额保持安全整数分', () => {
  for (const payslip of payroll.payslips)
    assertSafeCents(payslip)
})

console.log(`校验结束：${failures === 0 ? '全部通过' : `${failures} 项失败`}`)

if (failures > 0)
  process.exitCode = 1
