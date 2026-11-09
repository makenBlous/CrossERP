import { readMock } from '@/api/mock-client'
import { inventoryTotals, onHandRows } from '@/mocks/inventory'

export function fetchOnHand() {
  return readMock({ rows: onHandRows, totals: inventoryTotals })
}
