import type { Actor, MockDatabase, SalesOrder, SalesReturn } from '@/types/entities'
import { writeAudit } from '@/mocks/services/audit'
import { FlowError } from '@/mocks/services/errors'
import { mustFind, nextId } from '@/mocks/services/ids'
import { applyMovement, postStockDoc } from '@/mocks/services/inventory'
import { rebuildProfit } from '@/mocks/services/profit'
import { addMinor, mulQty } from '@/utils/money'

export function shipSalesOrder(db: MockDatabase, id: string, actor: Actor): SalesOrder {
  const order = mustFind(db.orders, id, '订单')

  if (order.status !== 'paid')
    throw new FlowError('只有待发货订单可以发货')

  const lines = db.orderLines.filter(line => line.orderId === order.id)

  postStockDoc(
    db,
    'outbound',
    order.warehouseId,
    lines.map(line => ({ internalSku: line.internalSku, qty: line.qty })),
    `订单发货 ${order.orderNo}`,
    actor,
    order.id,
  )
  order.status = 'shipped'
  order.shippedAt = actor.at
  if (!order.trackingNo)
    order.trackingNo = `TRK${order.id.slice(-5)}`

  writeAudit(db, actor, 'ship', 'sales_order', order.id, `订单 ${order.orderNo} 发货，生成出库单并减少库存`)
  rebuildProfit(db)

  return order
}

export function markRefund(db: MockDatabase, id: string, refund: number, actor: Actor): SalesOrder {
  const order = mustFind(db.orders, id, '订单')

  if (order.status !== 'shipped' && order.status !== 'partial_refund')
    throw new FlowError('只有已发货订单可以登记退款')

  order.refund = refund
  order.status = refund > 0 ? 'partial_refund' : order.status
  writeAudit(db, actor, 'refund', 'sales_order', order.id, `登记退款 ${order.orderNo}`)
  rebuildProfit(db)

  return order
}

function orderLinesOf(db: MockDatabase, orderId: string) {
  return db.orderLines.filter(line => line.orderId === orderId)
}

function scrapLines(db: MockDatabase, order: SalesOrder, actor: Actor) {
  for (const line of orderLinesOf(db, order.id)) {
    let balance = db.balances.find(row => row.warehouseId === order.warehouseId && row.internalSku === line.internalSku)

    if (!balance) {
      balance = {
        id: nextId(db, 'bal'),
        warehouseId: order.warehouseId,
        internalSku: line.internalSku,
        onHand: 0,
        reserved: 0,
        inTransit: 0,
        unfulfillable: 0,
      }
      db.balances.push(balance)
    }

    balance.unfulfillable += line.qty
    applyMovement(db, {
      warehouseId: order.warehouseId,
      internalSku: line.internalSku,
      onHandDelta: 0,
      inTransitDelta: 0,
      reason: 'scrap',
      refType: 'sales_return',
      refId: order.id,
      actor,
    })
  }
}

export function disposeReturn(db: MockDatabase, id: string, disposition: 'restock' | 'scrap', actor: Actor): SalesReturn {
  const row = mustFind(db.returns, id, '退货')

  if (row.status === 'restocked' || row.status === 'scrapped')
    throw new FlowError('这张退货已经处理过库存')

  const order = mustFind(db.orders, row.orderId, '订单')
  const lines = orderLinesOf(db, order.id).map(line => ({ internalSku: line.internalSku, qty: line.qty }))

  if (disposition === 'restock') {
    postStockDoc(db, 'inbound', order.warehouseId, lines, `退货入库 ${order.orderNo}`, actor, order.id)
    row.status = 'restocked'
    writeAudit(db, actor, 'restock', 'sales_return', row.id, `退货 ${order.orderNo} 入库，可售数量增加`)
  }
  else {
    scrapLines(db, order, actor)
    row.status = 'scrapped'
    writeAudit(db, actor, 'scrap', 'sales_return', row.id, `退货 ${order.orderNo} 报废，计入不可售，不增加可售库存`)
  }

  return row
}

export function registerReturn(db: MockDatabase, orderId: string, disposition: 'restock' | 'scrap', actor: Actor): SalesReturn {
  const order = mustFind(db.orders, orderId, '订单')

  if (order.status !== 'shipped' && order.status !== 'partial_refund')
    throw new FlowError('只有已发货订单可以登记退货')

  const pending = db.returns.find(item => item.orderId === order.id && item.status === 'posted')

  if (pending)
    return disposeReturn(db, pending.id, disposition, actor)

  const gross = orderLinesOf(db, order.id).reduce((sum, line) => addMinor(sum, mulQty(line.unitPrice, line.qty)), 0)
  const refund = gross - order.refund

  if (refund <= 0)
    throw new FlowError('这张订单没有可退金额')

  order.refund = gross
  order.status = 'refunded'

  const row: SalesReturn = {
    id: nextId(db, 'rtn'),
    storeId: order.storeId,
    orderId: order.id,
    amount: refund,
    currency: order.currency,
    postedAt: actor.at,
    status: 'posted',
  }

  db.returns.push(row)
  writeAudit(db, actor, 'refund', 'sales_order', order.id, `登记退货 ${order.orderNo}`)
  rebuildProfit(db)

  return disposeReturn(db, row.id, disposition, actor)
}
