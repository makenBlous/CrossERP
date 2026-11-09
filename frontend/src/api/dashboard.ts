import { readMock } from '@/api/mock-client'
import { dashboardAll, dashboardByStore } from '@/mocks/dashboard'
import { stores } from '@/mocks/stores'

export function fetchStores() {
  return readMock(stores)
}

export function fetchDashboard(storeId = 'all') {
  return readMock(dashboardByStore[storeId] ?? dashboardAll)
}
