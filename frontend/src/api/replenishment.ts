import { assertPermission, delay } from '@/api/mock-client'
import {
  approveDemandFactor,
  convertReplenishmentLine,
  fetchLatestReplenishmentPlan,
  fetchReplenishmentPlan,
  fetchReplenishmentPlans,
  getReplenishmentFactors,
  proposeDemandFactor,
  runReplenishmentPlan,
  setReplenishmentFreeze,
} from '@/mocks/services/replenishment'

export async function listReplenishmentPlans() {
  return fetchReplenishmentPlans()
}

export async function getReplenishmentPlanById(id: string) {
  return fetchReplenishmentPlan(id)
}

export async function getLatestReplenishmentPlan() {
  return fetchLatestReplenishmentPlan()
}

export async function runPlan() {
  await delay()

  return runReplenishmentPlan()
}

export async function freezePlanLine(planId: string, lineId: string, frozen: boolean) {
  await delay()

  return setReplenishmentFreeze(planId, lineId, frozen)
}

export async function convertPlanLine(planId: string, lineId: string) {
  await delay()

  return convertReplenishmentLine(planId, lineId)
}

export async function listDemandFactors(sku?: string) {
  await delay()
  assertPermission('material_request:read')

  return getReplenishmentFactors(sku)
}

export async function proposeFactor(internalSku: string, kind: 'season' | 'promo', value: string) {
  await delay()

  return proposeDemandFactor(internalSku, kind, value)
}

export async function approveFactor(id: string) {
  await delay()

  return approveDemandFactor(id)
}
