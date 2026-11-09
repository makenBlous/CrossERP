import { database, delay } from '@/api/mock-client'
import { projectChannels, projectExceptions, projectFulfillment, projectReturns } from '@/mocks/project-ops'
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

// 未来: GET /api/v1/sales/returns
export async function fetchReturns() {
  await delay()

  return projectReturns(database().db)
}

// 未来: GET /api/v1/sales/exceptions
export async function fetchExceptions() {
  await delay()

  return projectExceptions(database().db)
}

// 未来: GET /api/v1/sales/channels
export async function fetchChannels() {
  await delay()

  return projectChannels(database().db)
}

// 未来: GET /api/v1/sales/fulfillment
export async function fetchFulfillment() {
  await delay()

  return projectFulfillment(database().db)
}
