import type { CurrencyCode } from '@/types/domain'
import type { Actor, ApprovalEntity, MockDatabase } from '@/types/entities'
import { writeAudit } from '@/mocks/services/audit'
import { requireActorPermission } from '@/utils/service-permissions'
import { FlowError } from '@/mocks/services/errors'
import { mustFind, nextId } from '@/mocks/services/ids'
import { minorFromDecimal } from '@/utils/money'
import { applyVoucherApproval } from '@/mocks/services/gap-a'

export interface ApprovalWorkflowStep {
  id: string
  title: string
  role: string
}

export const approvalWorkflowTemplates: Record<string, ApprovalWorkflowStep[]> = {
  voucher: [{ id: 'submit', title: '提交', role: '运营' }, { id: 'finance', title: '财务审核', role: '财务' }, { id: 'admin', title: '管理员复核', role: '管理员' }],
  purchase_order: [{ id: 'submit', title: '提交', role: '采购' }, { id: 'finance', title: '财务审核', role: '财务' }, { id: 'admin', title: '管理员复核', role: '管理员' }],
  clearing: [{ id: 'submit', title: '提交', role: '财务' }, { id: 'review', title: '核销审核', role: '财务' }],
  allocation: [{ id: 'submit', title: '提交', role: '运营' }, { id: 'review', title: '分摊审核', role: '财务' }],
  agent_suggestion: [{ id: 'submit', title: '提交建议', role: '智能体' }, { id: 'review', title: '人工审核', role: '财务' }, { id: 'admin', title: '管理员复核', role: '管理员' }],
}

export function auditWorkflowEdit(db: MockDatabase, actor: Actor, documentType: string, step: ApprovalWorkflowStep) {
  requireActorPermission(actor, 'approval:write')
  writeAudit(db, actor, 'update_workflow', 'approval_workflow', documentType, `调整 ${documentType} 流程步骤 ${step.title}，审批角色改为 ${step.role}。`)
}

export function approvalPayload(approval: ApprovalEntity) {
  return {
    id: approval.id,
    targetType: approval.targetType,
    targetId: approval.targetId,
    title: approval.title,
    type: approval.type,
    submitter: approval.submitter,
    submittedAt: approval.submittedAt,
    amount: approval.amount,
    currency: approval.currency,
    summary: approval.summary,
    storeId: approval.storeId,
    lines: approval.lines.map(line => ({ account: line.account, debit: line.debit, credit: line.credit })),
  }
}

export async function approvalPayloadHash(approval: ApprovalEntity) {
  const bytes = new TextEncoder().encode(JSON.stringify(approvalPayload(approval)))
  const digest = await crypto.subtle.digest('SHA-256', bytes)

  return `sha256:${[...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, '0')).join('')}`
}

export const GAP_A_VOUCHER_TARGET = 'gap-a:voucher'

export interface SuggestionLine {
  account: string
  debit: number
  credit: number
}

export interface SuggestionInput {
  title: string
  summary: string
  amount: string
  currency: CurrencyCode
  storeId: string | null
  targetType: string
  targetId: string
  lines?: SuggestionLine[]
}

export function submitSuggestion(db: MockDatabase, input: SuggestionInput, actor: Actor): ApprovalEntity {
  requireActorPermission(actor, 'agent_suggestion:create')

  const amount = minorFromDecimal(input.amount)
  const lines = input.lines?.length
    ? input.lines.map(line => {
      if (!Number.isSafeInteger(line.debit) || !Number.isSafeInteger(line.credit))
        throw new Error('审批分录金额必须是整数最小单位')

      return { account: line.account, debit: line.debit, credit: line.credit }
    })
    : [
        { account: '待处理财产损溢', debit: amount, credit: 0 },
        { account: '平台结算清算', debit: 0, credit: amount },
      ]

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
    lines,
    payloadHash: `sha256:${input.targetType}:${input.targetId}:${amount}`,
  }

  db.approvals.push(approval)
  writeAudit(db, actor, 'suggest', 'approval', approval.id, `提交待审批建议 ${input.title}。未写账。`)

  return approval
}

export function decideApproval(db: MockDatabase, id: string, status: 'approved' | 'rejected', actor: Actor, comment = ''): ApprovalEntity {
  requireActorPermission(actor, 'approval:approve')

  const approval = mustFind(db.approvals, id, '审批')

  if (approval.status !== 'pending')
    throw new FlowError('这张审批已经处理过')

  // 防自审：提交人不能审批自己提交的单据（服务层强制，页面按钮只是提示）。
  if (approval.submitter === actor.name)
    throw new FlowError('不能审批自己提交的单据，请换另一位有审批权限的用户处理')

  // 先回写来源凭证。失败时审批状态保持 pending，避免批准落空或写到另一张凭证。
  if (approval.targetType === GAP_A_VOUCHER_TARGET)
    applyVoucherApproval(approval.targetId, status === 'approved', actor)

  approval.status = status
  approval.comment = comment.trim()
  if (approval.targetType === 'purchase_order') {
    const po = db.purchaseOrders.find(item => item.id === approval.targetId)

    if (po && po.status === 'submitted')
      po.status = status === 'approved' ? 'approved' : 'rejected'
  }
  if (approval.targetType === 'voucher') {
    const voucher = db.vouchers.find(item => item.id === approval.targetId)

    // 只有已经过 submitVoucher 草稿/平衡检查并进入待审批的财务凭证才能回写和导出。
    if (voucher && voucher.status === 'pending') {
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
