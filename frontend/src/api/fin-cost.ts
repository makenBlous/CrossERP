import { assertPermission, database, delay } from '@/api/mock-client'
import { appendAudit, approveLandedCost, getLandedCost, listGrni, listLandedCosts, listLedger, submitLandedCost } from '@/mocks/services/fin-cost'

export async function fetchStockLedger() {
  await delay()

  const actor = assertPermission('stock_ledger:read')

  return listLedger(actor)
}

export async function fetchLandedCosts() {
  await delay()
  assertPermission('landed_cost_voucher:read')

  return listLandedCosts()
}

export async function fetchLandedCost(id: string) {
  await delay()
  assertPermission('landed_cost_voucher:read')

  return getLandedCost(id)
}

export async function submitLandedCostApproval(id: string) {
  await delay()

  const actor = assertPermission('landed_cost_voucher:submit')
  const result = submitLandedCost(id, actor)

  appendAudit(actor, 'landed_cost.submit', 'landed_cost_voucher', id, `提交到岸成本分摊单 ${id}。`, database().db)
  database().persist()

  return result
}

export async function approveLandedCostVoucher(id: string) {
  await delay()

  const actor = assertPermission('landed_cost_voucher:approve')
  const result = approveLandedCost(id, actor)

  appendAudit(actor, 'landed_cost.approve', 'landed_cost_voucher', id, `批准并过账到岸成本分摊单 ${id}。`, database().db)
  database().persist()

  return result
}

export async function fetchGrniBalances() {
  await delay()
  assertPermission('purchase_receipt:read')

  return listGrni()
}
