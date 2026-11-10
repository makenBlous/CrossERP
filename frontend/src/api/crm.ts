import { projectAccount, projectAccounts } from '@/mocks/project'
import { assertPermission, database, delay } from '@/api/mock-client'
import { addMinor, convertMinor, toDisplay } from '@/utils/money'

import type { LeadStage } from '@/types/crm-admin'

// 未来: GET /api/v1/crm/accounts
export async function fetchAccounts() {
  await delay()
  assertPermission('customer:read')

  return projectAccounts(database().db)
}

// 未来: GET /api/v1/crm/accounts/{id}
export async function fetchAccount(id: string) {
  await delay()
  assertPermission('customer:read')

  return projectAccount(database().db, id)
}

// 未来: GET /api/v1/crm/leads
export async function fetchCrmLeads() {
  await delay()
  assertPermission('lead:read')

  return database().db.crmLeads ?? []
}

// 未来: GET /api/v1/crm/opportunities
export async function fetchCrmOpportunities() {
  await delay()
  assertPermission('lead:read')

  return database().db.crmOpportunities.map(item => ({ ...item, amount: toDisplay(item.amount, item.currency), accountName: database().db.crmAccounts.find(account => account.id === item.accountId)?.name ?? item.accountId }))
}

// 未来: GET /api/v1/crm/contacts
export async function fetchCrmContacts() {
  await delay()
  assertPermission('contact:read')

  return database().db.crmContacts.map(item => ({ ...item, accountName: database().db.crmAccounts.find(account => account.id === item.accountId)?.name ?? item.accountId }))
}

// 未来: GET /api/v1/crm/activities
export async function fetchCrmActivities() {
  await delay()
  assertPermission('contact:read')

  return database().db.crmActivities ?? []
}

// 未来: GET /api/v1/crm/tickets
export async function fetchCrmTickets() {
  await delay()
  assertPermission('ticket:read')

  const db = database().db

  return db.crmTickets.map(item => ({ ...item, accountName: db.crmAccounts.find(account => account.id === item.accountId)?.name ?? item.accountId }))
}

// 未来: GET /api/v1/crm/reviews
export async function fetchCrmReviews() {
  await delay()
  assertPermission('ticket:read')

  return database().db.crmReviews ?? []
}

// 未来: GET /api/v1/crm/dashboard
export async function fetchCrmDashboard() {
  await delay()
  assertPermission('customer:read')

  const db = database().db

  return { leads: db.crmLeads?.length ?? 0, openTickets: db.crmTickets.filter(item => item.status !== 'resolved').length, opportunities: db.crmOpportunities.length, pipeline: toDisplay(db.crmOpportunities.reduce((sum, item) => addMinor(sum, convertMinor(item.amount, item.currency, 'USD')), 0), 'USD') }
}

// 未来: GET /api/v1/crm/leads/{id}
export async function fetchLead(id: string) {
  await delay()
  assertPermission('lead:read')

  return database().db.crmLeads?.find(item => item.id === id) ?? null
}

// 未来: GET /api/v1/crm/opportunities/{id}
export async function fetchOpportunity(id: string) {
  await delay()
  assertPermission('lead:read')

  const db = database().db
  const item = db.crmOpportunities.find(row => row.id === id)

  if (!item)
    return null

  return {
    ...item,
    amount: toDisplay(item.amount, item.currency),
    accountName: db.crmAccounts.find(account => account.id === item.accountId)?.name ?? item.accountId,
    relatedOrders: db.orders
      .filter(order => order.opportunityId === item.id)
      .map(order => ({ id: order.id, orderNo: order.orderNo })),
  }
}

// 未来: GET /api/v1/crm/contacts/{id}
export async function fetchContact(id: string) {
  await delay()
  assertPermission('contact:read')

  const db = database().db
  const item = db.crmContacts.find(row => row.id === id)

  return item ? { ...item, accountName: db.crmAccounts.find(account => account.id === item.accountId)?.name ?? item.accountId } : null
}

// 未来: GET /api/v1/crm/tickets/{id}
export async function fetchTicket(id: string) {
  await delay()
  assertPermission('ticket:read')

  const db = database().db
  const item = db.crmTickets.find(row => row.id === id)

  const order = item?.orderNo ? db.orders.find(row => row.orderNo === item.orderNo) : undefined

  return item ? { ...item, orderId: order?.id ?? null, account: db.crmAccounts.find(account => account.id === item.accountId), messages: (db.crmTicketMessages ?? []).filter(message => message.ticketId === id) } : null
}

// 未来: PATCH /api/v1/crm/leads/{id}/stage
export async function updateCrmLeadStage(id: string, stage: LeadStage) {
  await delay()

  const actor = assertPermission('lead:write')

  return database().updateLeadStage(id, stage, actor)
}

// 未来: POST /api/v1/crm/leads/{id}/convert
export async function convertCrmLead(id: string) {
  await delay()

  const actor = assertPermission('lead:create')

  return database().convertLead(id, actor)
}

// 未来: POST /api/v1/crm/tickets
export async function createCrmTicket(input: { accountId: string
  orderNo: string | null
  subject: string }) {
  await delay()

  const actor = assertPermission('ticket:create')

  return database().addTicket(input, actor)
}

// 未来: PATCH /api/v1/crm/tickets/{id}/status
export async function updateCrmTicketStatus(id: string, status: string) {
  await delay()

  const actor = assertPermission('ticket:write')

  return database().updateTicketStatus(id, status, actor)
}

// 未来: GET /api/v1/crm/role-overrides
export async function fetchRoleOverrides() {
  await delay()
  assertPermission('permission:read')

  return JSON.parse(JSON.stringify(database().db.roleOverrides ?? []))
}

// 未来: PUT /api/v1/crm/role-overrides/{role}
export async function saveCrmRoleOverride(role: Parameters<ReturnType<typeof database>['saveRoleOverride']>[0], hiddenGroups: string[], hiddenPageIds: string[]) {
  await delay()
  database().saveRoleOverride(role, hiddenGroups, hiddenPageIds, assertPermission('permission:write'))
}

// 未来: DELETE /api/v1/crm/role-overrides/{role}
export async function resetCrmRoleOverride(role: Parameters<ReturnType<typeof database>['resetRoleOverride']>[0]) {
  await delay()
  database().resetRoleOverride(role, assertPermission('permission:write'))
}
