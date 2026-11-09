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
    payloadHash: `sha256:${input.targetType}:${input.targetId}:${amount}`,
  }

  db.approvals.push(approval)
  writeAudit(db, actor, 'suggest', 'approval', approval.id, `提交待审批建议 ${input.title}。未写账。`)

  return approval
}

export function decideApproval(db: MockDatabase, id: string, status: 'approved' | 'rejected', actor: Actor, comment = ''): ApprovalEntity {
  const approval = mustFind(db.approvals, id, '审批')

  if (approval.status !== 'pending')
    throw new FlowError('这张审批已经处理过')

  // 防自审：提交人不能审批自己提交的单据（服务层强制，页面按钮只是提示）。
  if (approval.submitter === actor.name)
    throw new FlowError('不能审批自己提交的单据，请换另一位有审批权限的用户处理')

  approval.status = status
  approval.comment = comment.trim()
  if (approval.targetType === 'purchase_order') {
    const po = db.purchaseOrders.find(item => item.id === approval.targetId)

    if (po && po.status === 'submitted')
      po.status = status === 'approved' ? 'approved' : 'rejected'
  }
  if (approval.targetType === 'voucher') {
    const voucher = db.vouchers.find(item => item.id === approval.targetId)

    if (voucher) {
      voucher.status = status === 'approved' ? 'approved' : 'rejected'
      if (status === 'approved') {
        const artifacts = db.finance2?.exports ?? []
        if (!artifacts.some(item => item.approvalId === approval.id)) {
          artifacts.push({
            id: `exp-${approval.id}`,
            fileName: `${voucher.id}.xlsx`,
            approvalId: approval.id,
            target: 'generic_xlsx',
            sha256: `sha256:${approval.id.slice(-8)}`,
            createdAt: actor.at,
            status: 'available',
          })
        }
      }
    }
  }
  if (approval.targetType === 'clearing' && status === 'approved') {
    const ids = approval.targetId.split(',')

    db.finance2?.clearing.filter(item => ids.includes(item.id)).forEach(item => {
      item.status = 'cleared'
    })
  }
  if (approval.targetType === 'allocation' && status === 'approved') {
    db.ads?.allocations.filter(item => item.id === approval.targetId).forEach(item => {
      item.source = '广告分摊（已批准）'
    })
  }

  writeAudit(db, actor, status, 'approval', approval.id, `${status === 'approved' ? '通过' : '驳回'}审批 ${approval.title}${approval.comment ? `：${approval.comment}` : ''}。演示不写账。`)

  return approval
}
