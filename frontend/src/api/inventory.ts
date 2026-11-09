import { assertCan, database, delay } from '@/api/mock-client'
import type { CountActual, StockDocDraft, WarehouseDraft } from '@/mocks/services/inventory'
import { projectOnHand } from '@/mocks/project'
import {
  projectAlerts,
  projectBalances,
  projectMovements,
  projectStockDoc,
  projectStockDocs,
  projectWarehouses,
} from '@/mocks/project-supply'

// 未来: GET /api/v1/inventory/on-hand
export async function fetchOnHand() {
  await delay()

  return projectOnHand(database().db)
}

// 未来: GET /api/v1/inventory/warehouses
export async function fetchWarehouses() {
  await delay()

  return projectWarehouses(database().db)
}

// 未来: POST /api/v1/inventory/warehouses
export async function createWarehouse(input: WarehouseDraft) {
  await delay()

  return database().saveWarehouse(input, assertCan('create'))
}

// 未来: PATCH /api/v1/inventory/warehouses/{id}
export async function updateWarehouse(id: string, input: WarehouseDraft) {
  await delay()

  return database().saveWarehouse({ ...input, id }, assertCan('update'))
}

// 未来: POST /api/v1/inventory/warehouses/status
export async function changeWarehouseActive(ids: string[], active: boolean) {
  await delay()
  database().setWarehouseActive(ids, active, assertCan('update'))
}

// 未来: GET /api/v1/inventory/balances?kind=
export async function fetchBalances(kind?: 'fba' | 'overseas' | 'domestic') {
  await delay()

  return projectBalances(database().db, kind)
}

// 未来: GET /api/v1/inventory/movements
export async function fetchMovements() {
  await delay()

  return projectMovements(database().db)
}

// 未来: GET /api/v1/inventory/docs?type=
export async function fetchStockDocs(docType: 'inbound' | 'outbound' | 'transfer' | 'count') {
  await delay()

  return projectStockDocs(database().db, docType)
}

// 未来: GET /api/v1/inventory/docs/{id}
export async function fetchStockDoc(id: string) {
  await delay()

  return projectStockDoc(database().db, id)
}

// 未来: POST /api/v1/inventory/docs
export async function createStockDoc(input: StockDocDraft) {
  await delay()

  return database().createStockDoc(input, assertCan('create'))
}

// 未来: POST /api/v1/inventory/docs/{id}/post
export async function completeStockDoc(id: string) {
  await delay()

  return database().postDraftDoc(id, assertCan('update'))
}

// 未来: POST /api/v1/inventory/transfers/{id}/post
export async function confirmTransfer(id: string) {
  await delay()

  return database().postTransfer(id, assertCan('update'))
}

// 未来: POST /api/v1/inventory/counts/{id}/post
export async function postStockCount(id: string, actuals: CountActual[]) {
  await delay()

  return database().postCount(id, actuals, assertCan('update'))
}

// 未来: GET /api/v1/inventory/alerts
export async function fetchAlerts() {
  await delay()

  return projectAlerts(database().db)
}
