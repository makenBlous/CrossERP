import type { CurrencyCode } from '@/types/domain'
import type { Actor, ApprovalEntity, MockDatabase } from '@/types/entities'
import { writeAudit } from '@/mocks/services/audit'
import { FlowError } from '@/mocks/services/errors'
import { mustFind, nextId } from '@/mocks/services/ids'
import { minorFromDecimal } from '@/utils/money'

export interface SuggestionInput {
  title: string
  summary: string
  amount: string
  currency: CurrencyCode
  storeId: string | null
  targetType: string
  targetId: string
}

export function submitSuggestion(db: MockDatabase, input: SuggestionInput, actor: Actor): ApprovalEntity {
  const amount = minorFromDecimal(input.amount)

  const approval: ApprovalEntity = {
    id: nextId(db, 'apr'),
    targetType: input.targetType,
    targetId: input.targetId,
    title: input.title,
    type: '智能体建议',
    submitter: actor.name,
    submittedAt: actor.at,
    amount,
    currency: input.currency,
    status: 'pending',
    summary: input.summary,
    storeId: input.storeId,
    lines: [
      { account: '待处理财产损溢', debit: amount, credit: 0 },
      { account: '平台结算清算', debit: 0, credit: amount },
    ],
  }

  db.approvals.push(approval)
  writeAudit(db, actor, 'suggest', 'approval', approval.id, `提交待审批建议 ${input.title}。未写账。`)

  return approval
}

export function decideApproval(db: MockDatabase, id: string, status: 'approved' | 'rejected', actor: Actor): ApprovalEntity {
  const approval = mustFind(db.approvals, id, '审批')

  if (approval.status !== 'pending')
    throw new FlowError('这张审批已经处理过')

  approval.status = status
  if (approval.targetType === 'purchase_order') {
    const po = db.purchaseOrders.find(item => item.id === approval.targetId)

    if (po && po.status === 'submitted')
      po.status = status === 'approved' ? 'approved' : 'rejected'
  }
  if (approval.targetType === 'voucher') {
    const voucher = db.vouchers.find(item => item.id === approval.targetId)

    if (voucher)
      voucher.status = status === 'approved' ? 'posted' : 'draft'
  }
  writeAudit(db, actor, status, 'approval', approval.id, `${status === 'approved' ? '通过' : '驳回'}审批 ${approval.title}。演示不写账。`)

  return approval
}
