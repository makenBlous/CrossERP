import { readMock } from '@/api/mock-client'
import { crmAccounts, crmDetails } from '@/mocks/crm'

export function fetchAccounts() {
  return readMock(crmAccounts)
}

export function fetchAccount(id: string) {
  return readMock(crmDetails[id] ?? null)
}
