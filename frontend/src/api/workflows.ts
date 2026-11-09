import { assertCan, database, delay } from '@/api/mock-client'
import type { CurrencyCode } from '@/types/domain'

// 未来: POST /api/v1/procurement/orders/{id}/submit
export async function submitPurchaseOrder(id: string) {
  await delay()

  const actor = assertCan('update')

  return database().submitPurchase(id, actor)
}

// 未来: POST /api/v1/procurement/orders/{id}/approve
export async function approvePurchaseOrder(id: string) {
  await delay()

  const actor = assertCan('approve')

  return database().approvePurchase(id, actor)
}

// 未来: POST /api/v1/procurement/orders/{id}/reject
export async function rejectPurchaseOrder(id: string) {
  await delay()

  const actor = assertCan('approve')

  return database().rejectPurchase(id, actor)
}

// 未来: POST /api/v1/procurement/receipts
export async function receivePurchaseOrder(id: string, warehouseId: string) {
  await delay()

  const actor = assertCan('receive')

  return database().receivePurchase(id, warehouseId, actor)
}

// 未来: POST /api/v1/logistics/shipments/{id}/depart
export async function departShipment(id: string) {
  await delay()

  const actor = assertCan('ship')

  return database().departFirstMile(id, actor)
}

// 未来: POST /api/v1/logistics/shipments/{id}/arrive
export async function arriveShipment(id: string) {
  await delay()

  const actor = assertCan('receive')

  return database().arriveFirstMile(id, actor)
}

// 未来: POST /api/v1/sales/orders/{id}/ship
export async function shipSalesOrder(id: string) {
  await delay()

  const actor = assertCan('ship')

  return database().shipOrder(id, actor)
}

// 未来: POST /api/v1/sales/orders/ship
export async function shipSalesOrders(ids: string[]) {
  await delay()

  const actor = assertCan('ship')
  const failed: string[] = []

  for (const id of ids) {
    try {
      database().shipOrder(id, actor)
    }
    catch (error) {
      failed.push(error instanceof Error ? error.message : id)
    }
  }

  return failed
}

// 未来: POST /api/v1/sales/returns/{id}/dispose
export async function disposeSalesReturn(id: string, disposition: 'restock' | 'scrap') {
  await delay()

  const actor = assertCan(disposition === 'restock' ? 'receive' : 'update')

  return database().disposeReturn(id, disposition, actor)
}

// 未来: POST /api/v1/sales/orders/{id}/returns
export async function registerSalesReturn(orderId: string, disposition: 'restock' | 'scrap') {
  await delay()

  const actor = assertCan(disposition === 'restock' ? 'receive' : 'update')

  return database().registerReturn(orderId, disposition, actor)
}

export interface SuggestionDraft {
  title: string
  summary: string
  amount: string
  currency: CurrencyCode
  storeId: string | null
  targetType: string
  targetId: string
}

// 未来: POST /api/v1/approvals
export async function submitAgentSuggestion(input: SuggestionDraft) {
  await delay()

  const actor = assertCan('suggest')

  return database().suggest(input, actor)
}
