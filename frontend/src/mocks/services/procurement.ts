import type { Actor, MockDatabase, PurchaseOrder } from '@/types/entities'
import { writeAudit } from '@/mocks/services/audit'
import { FlowError } from '@/mocks/services/errors'
import { mustFind, nextId } from '@/mocks/services/ids'
import { postStockDoc } from '@/mocks/services/inventory'
import { addMinor, mulQty } from '@/utils/money'

function findPo(db: MockDatabase, id: string) {
  return mustFind(db.purchaseOrders, id, '采购单')
}

export function submitPurchaseOrder(db: MockDatabase, id: string, actor: Actor): PurchaseOrder {
  const po = findPo(db, id)

  if (po.status !== 'draft')
    throw new FlowError('只有草稿采购单可以提交')

  po.status = 'submitted'

  const lines = db.purchaseOrderLines.filter(line => line.purchaseOrderId === po.id)
  const amount = lines.reduce((sum, line) => addMinor(sum, mulQty(line.unitCost, line.qty)), 0)

  db.approvals.push({
    id: nextId(db, 'apr'),
    targetType: 'purchase_order',
    targetId: po.id,
    title: `采购单 ${po.no} 待审批`,
    type: '采购单',
    submitter: actor.name,
    submittedAt: actor.at,
    amount,
    currency: po.currency,
    status: 'pending',
    summary: '提交采购单。批准前不会收货，也不会改库存。',
    storeId: null,
    lines: [
      { account: '在途物资', debit: amount, credit: 0 },
      { account: '应付账款', debit: 0, credit: amount },
    ],
  })
  writeAudit(db, actor, 'submit', 'purchase_order', po.id, `提交采购单 ${po.no}`)

  return po
}

export function approvePurchaseOrder(db: MockDatabase, id: string, actor: Actor): PurchaseOrder {
  const po = findPo(db, id)

  if (po.status !== 'submitted')
    throw new FlowError('只有待审批采购单可以通过')

  po.status = 'approved'

  const approval = db.approvals.find(item => item.targetType === 'purchase_order' && item.targetId === po.id && item.status === 'pending')

  if (approval)
    approval.status = 'approved'

  writeAudit(db, actor, 'approve', 'purchase_order', po.id, `批准采购单 ${po.no}`)

  return po
}

export function rejectPurchaseOrder(db: MockDatabase, id: string, actor: Actor): PurchaseOrder {
  const po = findPo(db, id)

  if (po.status !== 'submitted')
    throw new FlowError('只有待审批采购单可以驳回')

  po.status = 'rejected'

  const approval = db.approvals.find(item => item.targetType === 'purchase_order' && item.targetId === po.id && item.status === 'pending')

  if (approval)
    approval.status = 'rejected'

  writeAudit(db, actor, 'reject', 'purchase_order', po.id, `驳回采购单 ${po.no}`)

  return po
}

export function receivePurchaseOrder(db: MockDatabase, id: string, warehouseId: string, actor: Actor) {
  const po = findPo(db, id)

  if (po.status !== 'approved' && po.status !== 'partial')
    throw new FlowError('采购单尚未批准，不能收货')

  const openLines = db.purchaseOrderLines.filter(line => line.purchaseOrderId === po.id && line.receivedQty < line.qty)

  if (openLines.length === 0)
    throw new FlowError('采购单已全部收货')

  const receiptId = nextId(db, 'prc')

  db.receipts.push({
    id: receiptId,
    no: receiptId,
    purchaseOrderId: po.id,
    warehouseId,
    receivedAt: actor.at,
    status: 'posted',
  })

  const inbound = openLines.map(line => {
    const qty = line.qty - line.receivedQty

    line.receivedQty = line.qty
    db.receiptLines.push({
      id: nextId(db, 'prl'),
      receiptId,
      purchaseOrderLineId: line.id,
      qty,
    })

    return { internalSku: line.internalSku, qty }
  })

  postStockDoc(db, 'inbound', warehouseId, inbound, `采购收货 ${po.no}`, actor, receiptId)

  const stillOpen = db.purchaseOrderLines.some(line => line.purchaseOrderId === po.id && line.receivedQty < line.qty)

  po.status = stillOpen ? 'partial' : 'received'
  writeAudit(db, actor, 'receive', 'purchase_order', po.id, `收货 ${po.no}，生成入库单并增加库存`)

  return { purchaseOrder: po, receiptId }
}
