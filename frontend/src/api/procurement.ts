import { assertCan, database, delay } from '@/api/mock-client'
import type { PurchaseDraft, PurchaseReturnDraft, SupplierDraft } from '@/mocks/services/procurement'
import {
  projectPurchaseOrder,
  projectPurchaseOrders,
  projectPurchaseReturns,
  projectReceipts,
  projectStatements,
  projectSupplier,
  projectSuppliers,
  projectSupplyLookups,
} from '@/mocks/project-supply'

// 未来: GET /api/v1/procurement/lookups
export async function fetchSupplyLookups() {
  await delay()

  return projectSupplyLookups(database().db)
}

// 未来: GET /api/v1/procurement/suppliers
export async function fetchSuppliers() {
  await delay()

  return projectSuppliers(database().db)
}

// 未来: GET /api/v1/procurement/suppliers/{id}
export async function fetchSupplier(id: string) {
  await delay()

  return projectSupplier(database().db, id)
}

// 未来: POST /api/v1/procurement/suppliers
export async function createSupplier(input: SupplierDraft) {
  await delay()

  return database().saveSupplier(input, assertCan('create'))
}

// 未来: PATCH /api/v1/procurement/suppliers/{id}
export async function updateSupplier(id: string, input: SupplierDraft) {
  await delay()

  return database().saveSupplier({ ...input, id }, assertCan('update'))
}

// 未来: POST /api/v1/procurement/suppliers/status
export async function changeSupplierStatus(ids: string[], status: 'active' | 'paused') {
  await delay()
  database().setSupplierStatus(ids, status, assertCan('update'))
}

// 未来: GET /api/v1/procurement/orders
export async function fetchPurchaseOrders() {
  await delay()

  return projectPurchaseOrders(database().db)
}

// 未来: GET /api/v1/procurement/orders/{id}
export async function fetchPurchaseOrder(id: string) {
  await delay()

  return projectPurchaseOrder(database().db, id)
}

// 未来: POST /api/v1/procurement/orders
export async function createPurchaseOrder(input: PurchaseDraft) {
  await delay()

  return database().createPurchase(input, assertCan('create'))
}

// 未来: POST /api/v1/procurement/orders/{id}/cancel
export async function cancelPurchaseOrder(id: string) {
  await delay()

  return database().cancelPurchase(id, assertCan('update'))
}

// 未来: GET /api/v1/procurement/receipts
export async function fetchReceipts() {
  await delay()

  return projectReceipts(database().db)
}

// 未来: GET /api/v1/procurement/returns
export async function fetchPurchaseReturns() {
  await delay()

  return projectPurchaseReturns(database().db)
}

// 未来: POST /api/v1/procurement/returns
export async function createPurchaseReturn(input: PurchaseReturnDraft) {
  await delay()

  return database().createPurchaseReturn(input, assertCan('create'))
}

// 未来: POST /api/v1/procurement/returns/{id}/confirm
export async function confirmPurchaseReturn(id: string) {
  await delay()

  return database().confirmPurchaseReturn(id, assertCan('update'))
}

// 未来: GET /api/v1/procurement/statements
export async function fetchStatements() {
  await delay()

  return projectStatements(database().db)
}

// 未来: POST /api/v1/procurement/statements
export async function generateStatement(supplierId: string, period: string) {
  await delay()

  return database().generateStatement(supplierId, period, assertCan('create'))
}

// 未来: POST /api/v1/procurement/statements/{id}/submit
export async function submitStatement(id: string) {
  await delay()

  return database().submitStatement(id, assertCan('suggest'))
}
