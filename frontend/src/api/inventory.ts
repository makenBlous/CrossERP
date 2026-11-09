import { database, delay } from '@/api/mock-client'
import { projectOnHand } from '@/mocks/project'

// 未来: GET /api/v1/inventory/on-hand
export async function fetchOnHand() {
  await delay()

  return projectOnHand(database().db)
}
