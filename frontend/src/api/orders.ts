import { database, delay } from '@/api/mock-client'
import { projectOrder, projectOrders } from '@/mocks/project'

// 未来: GET /api/v1/sales/orders
export async function fetchOrders() {
  await delay()

  return projectOrders(database().db)
}

// 未来: GET /api/v1/sales/orders/{id}
export async function fetchOrder(id: string) {
  await delay()

  return projectOrder(database().db, id)
}
