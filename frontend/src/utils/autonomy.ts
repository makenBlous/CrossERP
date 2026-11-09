import type { AgentAutonomyLevel, AgentAutonomyPolicy } from '@/types/foundation'

const monetaryWords = /money|amount|voucher|journal|ledger|payment|payroll|salary|wage|expense|claim|invoice|账|凭证|付款|薪资|金额|工资|报销/u

export function hardMaxForAction(action: string): AgentAutonomyLevel {
  return monetaryWords.test(action) ? 'L2' : 'L3'
}

export function validateAutonomyLevel(action: string, requested: AgentAutonomyLevel, hardMax = hardMaxForAction(action)) {
  const order: AgentAutonomyLevel[] = ['L0', 'L1', 'L2', 'L3']
  if (order.indexOf(requested) > order.indexOf(hardMax))
    return { ok: false as const, level: hardMax, reason: `涉及金额、凭证、付款或薪资的动作最高只能设为 ${hardMax}` }

  return { ok: true as const, level: requested, reason: '' }
}

export function updateAutonomyPolicy(policy: AgentAutonomyPolicy, requested: AgentAutonomyLevel): AgentAutonomyPolicy {
  const result = validateAutonomyLevel(policy.action, requested, policy.hardMaxLevel)
  if (!result.ok)
    throw new Error(result.reason)

  return { ...policy, level: result.level }
}
