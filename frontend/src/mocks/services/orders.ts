import type { Actor, MockDatabase, SalesOrder } from '@/types/entities'
import { writeAudit } from '@/mocks/services/audit'
import { FlowError } from '@/mocks/services/errors'
import { mustFind } from '@/mocks/services/ids'
import { postStockDoc } from '@/mocks/services/inventory'
import { rebuildProfit } from '@/mocks/services/profit'

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
