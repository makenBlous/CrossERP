import { submitAgentSuggestion as submitBoundAgentSuggestion } from '@/api/agent-module'
import { assertPermission, database, delay } from '@/api/mock-client'
import type { CurrencyCode } from '@/types/domain'
import type { ApprovalEntity } from '@/types/entities'

// 未来: POST /api/v1/procurement/orders/{id}/submit
export async function submitPurchaseOrder(id: string) {
  await delay()

  const actor = assertPermission('purchase_order:submit')

  return database().submitPurchase(id, actor)
}

// 未来: POST /api/v1/procurement/orders/{id}/approve
export async function approvePurchaseOrder(id: string) {
  await delay()

  const actor = assertPermission('purchase_order:approve')

  return database().approvePurchase(id, actor)
}

// 未来: POST /api/v1/procurement/orders/{id}/reject
export async function rejectPurchaseOrder(id: string) {
  await delay()

  const actor = assertPermission('purchase_order:approve')

  return database().rejectPurchase(id, actor)
}

// 未来: POST /api/v1/procurement/receipts
export async function receivePurchaseOrder(id: string, warehouseId: string) {
  await delay()

  const actor = assertPermission('purchase_receipt:submit')

  return database().receivePurchase(id, warehouseId, actor)
}

// 未来: POST /api/v1/logistics/shipments/{id}/depart
export async function departShipment(id: string) {
  await delay()

  const actor = assertPermission('shipment:write')

  return database().departFirstMile(id, actor)
}

// 未来: POST /api/v1/logistics/shipments/{id}/arrive
export async function arriveShipment(id: string) {
  await delay()

  const actor = assertPermission('shipment:write')

  return database().arriveFirstMile(id, actor)
}

// 未来: POST /api/v1/sales/orders/{id}/ship
export async function shipSalesOrder(id: string) {
  await delay()

  const actor = assertPermission('delivery_note:submit')

  return database().shipOrder(id, actor)
}

// 未来: POST /api/v1/sales/orders/ship
export async function shipSalesOrders(ids: string[]) {
  await delay()

  const actor = assertPermission('delivery_note:submit')
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

  const actor = assertPermission(disposition === 'restock' ? 'purchase_receipt:submit' : 'delivery_note:write')

  return database().disposeReturn(id, disposition, actor)
}

// 未来: POST /api/v1/sales/orders/{id}/returns
export async function registerSalesReturn(orderId: string, disposition: 'restock' | 'scrap') {
  await delay()

  const actor = assertPermission(disposition === 'restock' ? 'purchase_receipt:submit' : 'delivery_note:write')

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

// 未来: POST /api/v1/approvals。必须复用发起者绑定，不能在 delay 返回后按当时会话落库。
export async function submitAgentSuggestion(input: SuggestionDraft): Promise<ApprovalEntity> {
  return submitBoundAgentSuggestion(input)
}
