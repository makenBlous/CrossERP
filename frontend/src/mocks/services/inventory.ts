import type { Actor, MockDatabase } from '@/types/entities'
import { writeAudit } from '@/mocks/services/audit'
import { FlowError } from '@/mocks/services/errors'
import { nextId } from '@/mocks/services/ids'

export interface MovementInput {
  warehouseId: string
  internalSku: string
  onHandDelta: number
  inTransitDelta: number
  reason: string
  refType: string
  refId: string
  actor: Actor
}

export function applyMovement(db: MockDatabase, input: MovementInput) {
  let balance = db.balances.find(row => row.warehouseId === input.warehouseId && row.internalSku === input.internalSku)

  if (!balance) {
    balance = {
      id: nextId(db, 'bal'),
      warehouseId: input.warehouseId,
      internalSku: input.internalSku,
      onHand: 0,
      reserved: 0,
      inTransit: 0,
      unfulfillable: 0,
    }
    db.balances.push(balance)
  }

  if (balance.onHand + input.onHandDelta < 0)
    throw new FlowError(`${input.internalSku} 在仓库库存不足，不能出库`)

  if (balance.inTransit + input.inTransitDelta < 0)
    throw new FlowError(`${input.internalSku} 在途数量不足`)

  balance.onHand += input.onHandDelta
  balance.inTransit += input.inTransitDelta
  db.movements.push({
    id: nextId(db, 'mov'),
    warehouseId: input.warehouseId,
    internalSku: input.internalSku,
    qtyDelta: input.onHandDelta,
    inTransitDelta: input.inTransitDelta,
    reason: input.reason,
    refType: input.refType,
    refId: input.refId,
    occurredAt: input.actor.at,
    createdBy: input.actor.name,
  })
}

export function postStockDoc(
  db: MockDatabase,
  docType: 'inbound' | 'outbound',
  warehouseId: string,
  lines: Array<{ internalSku: string; qty: number }>,
  remark: string,
  actor: Actor,
  refId: string,
) {
  const docId = nextId(db, 'doc')

  db.stockDocs.push({
    id: docId,
    docNo: docId,
    docType,
    warehouseId,
    toWarehouseId: null,
    status: 'posted',
    remark,
    createdBy: actor.name,
    createdAt: actor.at,
  })
  for (const line of lines) {
    db.stockDocLines.push({
      id: nextId(db, 'dln'),
      docId,
      internalSku: line.internalSku,
      qtyExpected: line.qty,
      qtyActual: line.qty,
    })
    applyMovement(db, {
      warehouseId,
      internalSku: line.internalSku,
      onHandDelta: docType === 'inbound' ? line.qty : -line.qty,
      inTransitDelta: 0,
      reason: docType,
      refType: 'stock_doc',
      refId,
      actor,
    })
  }
  writeAudit(db, actor, docType, 'stock_doc', docId, remark)

  return docId
}
