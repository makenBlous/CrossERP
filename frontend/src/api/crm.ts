/* eslint-disable max-statements-per-line */
import { projectAccount, projectAccounts } from '@/mocks/project'
import { database, delay } from '@/api/mock-client'

// 未来: GET /api/v1/crm/accounts
export async function fetchAccounts() {
  await delay()

  return projectAccounts(database().db)
}

// 未来: GET /api/v1/crm/accounts/{id}
export async function fetchAccount(id: string) {
  await delay()

  return projectAccount(database().db, id)
}

// 未来: GET /api/v1/crm/leads
export async function fetchCrmLeads() {
  await delay()

  return database().db.crmLeads ?? []
}

// 未来: GET /api/v1/crm/opportunities
export async function fetchCrmOpportunities() {
  await delay()

  return database().db.crmOpportunities.map(item => ({ ...item, accountName: database().db.crmAccounts.find(account => account.id === item.accountId)?.name ?? item.accountId }))
}

// 未来: GET /api/v1/crm/contacts
export async function fetchCrmContacts() {
  await delay()

  return database().db.crmContacts.map(item => ({ ...item, accountName: database().db.crmAccounts.find(account => account.id === item.accountId)?.name ?? item.accountId }))
}

// 未来: GET /api/v1/crm/activities
export async function fetchCrmActivities() {
  await delay()

  return database().db.crmActivities ?? []
}

// 未来: GET /api/v1/crm/tickets
export async function fetchCrmTickets() {
  await delay()

  return database().db.crmTickets
}

// 未来: GET /api/v1/crm/reviews
export async function fetchCrmReviews() {
  await delay()

  return database().db.crmReviews ?? []
}

// 未来: GET /api/v1/crm/dashboard
export async function fetchCrmDashboard() {
  await delay()

  const db = database().db

  return { leads: db.crmLeads?.length ?? 0, openTickets: db.crmTickets.filter(item => item.status !== 'resolved').length, opportunities: db.crmOpportunities.length, pipeline: db.crmOpportunities.reduce((sum, item) => sum + item.amount, 0) }
}
export async function fetchLead(id: string) {
  await delay()

  return database().db.crmLeads?.find(item => item.id === id) ?? null
}
export async function fetchOpportunity(id: string) {
  await delay()

  const db = database().db; const item = db.crmOpportunities.find(row => row.id === id)

  return item ? { ...item, accountName: db.crmAccounts.find(account => account.id === item.accountId)?.name ?? item.accountId } : null
}
export async function fetchContact(id: string) {
  await delay()

  const db = database().db; const item = db.crmContacts.find(row => row.id === id)

  return item ? { ...item, accountName: db.crmAccounts.find(account => account.id === item.accountId)?.name ?? item.accountId } : null
}
export async function fetchTicket(id: string) {
  await delay()

  const db = database().db; const item = db.crmTickets.find(row => row.id === id)

  const order = item?.orderNo ? db.orders.find(row => row.orderNo === item.orderNo) : undefined

  return item ? { ...item, orderId: order?.id ?? null, account: db.crmAccounts.find(account => account.id === item.accountId), messages: (db.crmTicketMessages ?? []).filter(message => message.ticketId === id) } : null
}
