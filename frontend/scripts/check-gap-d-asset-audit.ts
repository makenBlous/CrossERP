import assert from 'node:assert/strict'

import {
  approveGapDLeave,
  approveGapDPayroll,
  calculateGapDPayroll,
  checkoutGapDAsset,
  editGapDContract,
  gapDAssets,
  gapDAudit,
  gapDAuditActorLabel,
  gapDContracts,
  gapDPayrollRuns,
  listGapDAudit,
  publishGapDPayslips,
  returnGapDAsset,
  reviewGapDPayroll,
  submitGapDLeave,
} from '../src/mocks/services/gap-d'
import type { Actor } from '../src/types/entities'
import type { GapDAuditEvent } from '../src/types/gap-d'

const at = '2026-11-10T08:00:00+08:00'
const admin: Actor = { userId: 'demo-admin', name: '演示管理员', role: 'admin', at }
const employee: Actor = { userId: 'demo-employee', name: '演示普通员工', role: 'employee', at }
const manager: Actor = { userId: 'demo-ops-manager', name: '演示运营主管', role: 'department_manager', at }
const hr: Actor = { userId: 'demo-hr-admin', name: '演示人事行政', role: 'hr_admin', at }
const financeManager: Actor = { userId: 'demo-fin-manager', name: '演示财务主管', role: 'finance_manager', at }

function check(label: string, assertion: () => void) {
  assertion()
  console.log(`[通过] ${label}`)
}

const asset = gapDAssets.find(row => row.id === 'asset-001')

assert(asset)

check('资产领用→归还→再次领用成功，重复归还被拒绝', () => {
  checkoutGapDAsset(asset.id, 'demo-employee', admin)
  returnGapDAsset(asset.id, admin)
  assert.equal(asset.status, '可领用')
  assert.throws(() => returnGapDAsset(asset.id, admin), /重复归还被拒绝/)
  checkoutGapDAsset(asset.id, 'demo-employee', admin)
  assert.equal(asset.status, '已领用')
})

const leave = submitGapDLeave({ startDate: '2026-12-01', endDate: '2026-12-01', reason: '回归检查' }, employee)

approveGapDLeave(leave.id, manager)

approveGapDLeave(leave.id, hr)

const payroll = calculateGapDPayroll('2026-12', admin)

reviewGapDPayroll(payroll.id, '回归检查', hr)
approveGapDPayroll(payroll.id, financeManager)
publishGapDPayslips(payroll.id, hr)
editGapDContract('contract-001', { status: gapDContracts[0]?.status === '生效' ? '已终止' : '生效' }, admin)

const expectedActorIds = new Map<string, string[]>([
  ['提交请假', [employee.userId]],
  ['审批请假', [manager.userId, hr.userId]],
  ['发起算薪', [admin.userId]],
  ['薪资复核提交审批', [hr.userId]],
  ['财务审批薪资批次', [financeManager.userId]],
  ['发布工资条', [hr.userId]],
  ['资产领用', [admin.userId, admin.userId]],
  ['资产归还', [admin.userId]],
  ['编辑合同', [admin.userId]],
])

for (const [action, actorIds] of expectedActorIds) {
  check(`${action} 审计包含稳定 actorId`, () => {
    const events = listGapDAudit().filter(row => row.action === action)

    assert.equal(events.length, actorIds.length)
    assert.deepEqual(events.map(row => row.actorId).sort(), [...actorIds].sort())
  })
}

check('旧缓存审计记录缺 actorId 时仍可列出', () => {
  const oldEvent = { id: 'gapd-audit-old-cache', action: '旧缓存记录', origin: 'human', actor: '旧用户', at, detail: '旧格式' } as GapDAuditEvent

  gapDAudit.push(oldEvent)
  assert.equal(listGapDAudit().find(row => row.id === oldEvent.id), oldEvent)
  assert.match(gapDAuditActorLabel(oldEvent), /旧记录未留 ID/)
})

assert(gapDPayrollRuns.some(row => row.id === payroll.id))
console.log('校验结束：全部通过')
