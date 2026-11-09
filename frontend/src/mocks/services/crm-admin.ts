import type { Actor, MockDatabase } from '@/types/entities'
import type { LeadStage } from '@/types/crm-admin'
import { nextId } from '@/mocks/services/ids'
import { writeAudit } from '@/mocks/services/audit'
import { requireActorPermission } from '@/utils/service-permissions'

export function updateLeadStage(db: MockDatabase, id: string, stage: LeadStage, actor: Actor) {
  requireActorPermission(actor, 'lead:write')

  const lead = db.crmLeads?.find(item => item.id === id)
  if (!lead)
    return null
  lead.stage = stage
  writeAudit(db, actor, '线索阶段变更', 'crm_lead', id, `阶段改为 ${stage}`)

  return lead
}

export function convertLead(db: MockDatabase, id: string, actor: Actor) {
  requireActorPermission(actor, 'lead:create')

  const lead = db.crmLeads?.find(item => item.id === id)
  if (!lead)
    return null
  let account = lead.accountId ? db.crmAccounts.find(item => item.id === lead.accountId) : undefined
  if (!account) {
    account = { id: nextId(db, 'acc'), name: lead.company || lead.name, kind: '潜在线索', country: '待确认', owner: lead.owner, currency: 'USD', status: 'converted', tags: ['线索转化'], website: '', email: lead.email, phone: '', note: `由线索 ${lead.name} 转化` }
    db.crmAccounts.push(account)
  }
  let contact = lead.contactId ? db.crmContacts.find(item => item.id === lead.contactId) : undefined
  if (!contact) {
    contact = { id: nextId(db, 'ctc'), accountId: account.id, name: lead.name, title: '采购联系人', email: lead.email }
    db.crmContacts.push(contact)
  }
  let opportunity = lead.opportunityId ? db.crmOpportunities.find(item => item.id === lead.opportunityId) : undefined
  if (!opportunity) {
    opportunity = { id: nextId(db, 'opp'), accountId: account.id, name: `${lead.company || lead.name} 合作商机`, amount: 1860000, currency: 'USD', stage: '初步沟通' }
    db.crmOpportunities.push(opportunity)
  }
  lead.accountId = account.id
  lead.contactId = contact.id
  lead.opportunityId = opportunity.id
  lead.stage = 'converted'
  writeAudit(db, actor, '线索转化', 'crm_lead', id, `已创建客户 ${account.name}、联系人 ${contact.name} 和商机 ${opportunity.name}`)

  return { lead, account, contact, opportunity }
}

export function addTicket(db: MockDatabase, input: { accountId: string
  orderNo: string | null
  subject: string }, actor: Actor) {
  requireActorPermission(actor, 'ticket:create')

  const ticket = { id: nextId(db, 'tkt'), accountId: input.accountId, subject: input.subject, status: 'open', orderNo: input.orderNo }

  db.crmTickets.push(ticket)
  db.crmTicketMessages?.push({ id: nextId(db, 'msg'), ticketId: ticket.id, author: actor.name, text: '工单已创建，等待处理。', at: actor.at, internal: true })
  writeAudit(db, actor, '创建售后工单', 'crm_ticket', ticket.id, ticket.subject)

  return ticket
}

export function updateTicketStatus(db: MockDatabase, id: string, status: string, actor: Actor) {
  requireActorPermission(actor, 'ticket:write')

  const ticket = db.crmTickets.find(item => item.id === id)
  if (!ticket)
    return null
  ticket.status = status
  db.crmTicketMessages?.push({ id: nextId(db, 'msg'), ticketId: id, author: actor.name, text: `状态更新为：${status}`, at: actor.at, internal: true })
  writeAudit(db, actor, '工单状态变更', 'crm_ticket', id, `状态改为 ${status}`)

  return ticket
}

export function saveRoleOverride(db: MockDatabase, role: Actor['role'], hiddenGroups: string[], hiddenPageIds: string[], actor: Actor) {
  requireActorPermission(actor, 'permission:write')
  if (!db.roleOverrides)
    db.roleOverrides = []
  const existing = db.roleOverrides.find(item => item.role === role)
  if (existing) {
    existing.hiddenGroups = hiddenGroups
    existing.hiddenPageIds = hiddenPageIds
  }
  else { db.roleOverrides.push({ role, hiddenGroups, hiddenPageIds }) }
  writeAudit(db, actor, '修改角色菜单权限', 'role', role, `隐藏分组 ${hiddenGroups.join(', ')}`)
}

export function resetRoleOverride(db: MockDatabase, role: Actor['role'], actor: Actor) {
  requireActorPermission(actor, 'permission:write')
  if (db.roleOverrides)
    db.roleOverrides = db.roleOverrides.filter(item => item.role !== role)
  writeAudit(db, actor, '恢复角色默认权限', 'role', role, '恢复默认菜单可见性')
}

export function createToken(db: MockDatabase, name: string, actor: Actor) {
  requireActorPermission(actor, 'user:write')
  if (!db.accountTokens)
    db.accountTokens = []
  const secret = `csp_${Math.random().toString(36).slice(2, 18)}`
  const token = { id: nextId(db, 'tok'), name, prefix: `${secret.slice(0, 8)}…`, createdAt: actor.at, lastUsedAt: null, revoked: false }

  db.accountTokens.push(token)
  writeAudit(db, actor, '创建 API Token', 'account_token', token.id, `${name}（仅创建时显示明文）`)

  return { token, secret }
}

export function revokeToken(db: MockDatabase, id: string, actor: Actor) {
  requireActorPermission(actor, 'user:write')

  const token = db.accountTokens?.find(item => item.id === id)
  if (!token)
    return null
  token.revoked = true
  writeAudit(db, actor, '撤销 API Token', 'account_token', id, token.name)

  return token
}

export function changePassword(db: MockDatabase, actor: Actor) {
  requireActorPermission(actor, 'user:write')
  writeAudit(db, actor, '修改密码', 'account', actor.name, '密码已更新，未记录明文')
}
