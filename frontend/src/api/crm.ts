import { database, delay } from '@/api/mock-client'
import { projectAccount, projectAccounts } from '@/mocks/project'

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
