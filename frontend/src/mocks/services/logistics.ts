import type { Actor, MockDatabase, Shipment } from '@/types/entities'
import { writeAudit } from '@/mocks/services/audit'
import { FlowError } from '@/mocks/services/errors'
import { mustFind, nextId } from '@/mocks/services/ids'
import { applyMovement, postStockDoc } from '@/mocks/services/inventory'

function findShipment(db: MockDatabase, id: string) {
  return mustFind(db.shipments, id, '头程运单')
}

export function departShipment(db: MockDatabase, id: string, actor: Actor): Shipment {
  const shipment = findShipment(db, id)

  if (shipment.status !== 'planned')
    throw new FlowError('只有计划中的头程可以发运')

  const lines = db.shipmentLines.filter(line => line.shipmentId === shipment.id)

  shipment.status = 'in_transit'
  shipment.departedAt = actor.at
  for (const line of lines) {
    applyMovement(db, {
      warehouseId: shipment.warehouseFrom,
      internalSku: line.internalSku,
      onHandDelta: -line.qty,
      inTransitDelta: 0,
      reason: 'first_mile_depart',
      refType: 'shipment',
      refId: shipment.id,
      actor,
    })
    applyMovement(db, {
      warehouseId: shipment.warehouseTo,
      internalSku: line.internalSku,
      onHandDelta: 0,
      inTransitDelta: line.qty,
      reason: 'first_mile_transit',
      refType: 'shipment',
      refId: shipment.id,
      actor,
    })
  }
  db.tracking.push({
    id: nextId(db, 'trk'),
    shipmentId: shipment.id,
    occurredAt: actor.at,
    description: '已离开始发仓，FBA 在途数量增加',
  })
  writeAudit(db, actor, 'depart', 'shipment', shipment.id, `头程 ${shipment.no} 发运，目的仓在途增加`)

  return shipment
}

export function arriveShipment(db: MockDatabase, id: string, actor: Actor): Shipment {
  const shipment = findShipment(db, id)

  if (shipment.status !== 'in_transit')
    throw new FlowError('只有在途头程可以签收')

  const lines = db.shipmentLines.filter(line => line.shipmentId === shipment.id)

  for (const line of lines) {
    applyMovement(db, {
      warehouseId: shipment.warehouseTo,
      internalSku: line.internalSku,
      onHandDelta: 0,
      inTransitDelta: -line.qty,
      reason: 'first_mile_arrive_transit',
      refType: 'shipment',
      refId: shipment.id,
      actor,
    })
  }
  postStockDoc(
    db,
    'inbound',
    shipment.warehouseTo,
    lines.map(line => ({ internalSku: line.internalSku, qty: line.qty })),
    `头程签收 ${shipment.no}`,
    actor,
    shipment.id,
  )
  shipment.status = 'arrived'
  shipment.arrivedAt = actor.at
  db.tracking.push({
    id: nextId(db, 'trk'),
    shipmentId: shipment.id,
    occurredAt: actor.at,
    description: 'FBA 签收，在途转为可售',
  })
  writeAudit(db, actor, 'arrive', 'shipment', shipment.id, `头程 ${shipment.no} 签收，在途转为可售`)

  return shipment
}
