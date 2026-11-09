export interface ApprovalActorContext {
  submitterId: string
  approverId: string
  origin: 'human' | 'agent'
  onBehalfOfUserId?: string
  agentId?: string
}

export function canApprove(context: ApprovalActorContext) {
  if (context.submitterId === context.approverId)
    return false
  if (context.origin === 'agent' && context.onBehalfOfUserId === context.approverId)
    return false

  return context.agentId !== context.approverId
}
