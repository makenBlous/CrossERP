import { database, delay } from '@/api/mock-client'
import { projectDashboard, projectStores } from '@/mocks/project'

// 未来: GET /api/v1/stores
export async function fetchStores() {
  await delay()

  return projectStores(database().db)
}

// 未来: GET /api/v1/dashboard?store_id=
export async function fetchDashboard(storeId = 'all') {
  await delay()

  return projectDashboard(database().db, storeId)
}
