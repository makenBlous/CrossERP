import { assertPermission, database, delay } from '@/api/mock-client'
import type { CarrierDraft, RateDraft, ShipmentDraft, ShipmentFeeDraft } from '@/mocks/services/logistics'
import {
  projectCarriers,
  projectFreightChecks,
  projectRateCards,
  projectShipment,
  projectShipments,
  projectTracking,
} from '@/mocks/project-supply'

// 未来: GET /api/v1/logistics/shipments
export async function fetchShipments() {
  await delay()
  assertPermission('shipment:read')

  return projectShipments(database().db)
}

// 未来: GET /api/v1/logistics/shipments/{id}
export async function fetchShipment(id: string) {
  await delay()
  assertPermission('shipment:read')

  return projectShipment(database().db, id)
}

// 未来: POST /api/v1/logistics/shipments
export async function createShipment(input: ShipmentDraft) {
  await delay()

  return database().createShipment(input, assertPermission('shipment:create'))
}

// 未来: POST /api/v1/logistics/shipments/{id}/charges
export async function saveShipmentFee(input: ShipmentFeeDraft) {
  await delay()

  return database().saveShipmentFee(input, assertPermission('shipment:write'))
}

// 未来: GET /api/v1/logistics/carriers
export async function fetchCarriers() {
  await delay()
  assertPermission('shipment:read')

  return projectCarriers(database().db)
}

// 未来: POST /api/v1/logistics/carriers
export async function createCarrier(input: CarrierDraft) {
  await delay()

  return database().saveCarrier(input, assertPermission('shipment:create'))
}

// 未来: PATCH /api/v1/logistics/carriers/{id}
export async function updateCarrier(id: string, input: CarrierDraft) {
  await delay()

  return database().saveCarrier({ ...input, id }, assertPermission('shipment:write'))
}

// 未来: POST /api/v1/logistics/carriers/status
export async function changeCarrierActive(ids: string[], active: boolean) {
  await delay()
  database().setCarrierActive(ids, active, assertPermission('shipment:write'))
}

// 未来: GET /api/v1/logistics/rate-cards
export async function fetchRateCards() {
  await delay()
  assertPermission('shipment:read')

  return projectRateCards(database().db)
}

// 未来: POST /api/v1/logistics/rate-cards
export async function createRateCard(input: RateDraft) {
  await delay()

  return database().saveRateCard(input, assertPermission('shipment:create'))
}

// 未来: PATCH /api/v1/logistics/rate-cards/{id}
export async function updateRateCard(id: string, input: RateDraft) {
  await delay()

  return database().saveRateCard({ ...input, id }, assertPermission('shipment:write'))
}

// 未来: GET /api/v1/logistics/tracking
export async function fetchTracking() {
  await delay()
  assertPermission('shipment:read')

  return projectTracking(database().db)
}

// 未来: GET /api/v1/logistics/fee-checks
export async function fetchFreightChecks() {
  await delay()
  assertPermission('shipment:read')

  return projectFreightChecks(database().db)
}

// 未来: POST /api/v1/logistics/fee-checks/{id}/submit
export async function submitFreightCheck(id: string) {
  await delay()

  return database().submitFreightCheck(id, assertPermission('shipment:write'))
}
