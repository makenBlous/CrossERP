import { readMock } from '@/api/mock-client'
import { orderDetails, orderSummaries } from '@/mocks/orders'

export function fetchOrders() {
  return readMock(orderSummaries)
}

export function fetchOrder(id: string) {
  return readMock(orderDetails[id] ?? null)
}
