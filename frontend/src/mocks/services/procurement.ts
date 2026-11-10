import type { CurrencyCode } from '@/types/domain'
import type { Actor, MockDatabase, PurchaseOrder, PurchaseReturn, Supplier, SupplierStatement } from '@/types/entities'
import { writeAudit } from '@/mocks/services/audit'
import { FlowError } from '@/mocks/services/errors'
import { mustFind, nextId } from '@/mocks/services/ids'
import { applyMovement, postStockDoc } from '@/mocks/services/inventory'
import { addMinor, minorFromDecimal, minorToDecimal, mulQty } from '@/utils/money'
import { requireActorPermission } from '@/utils/service-permissions'

function findPo(db: MockDatabase, id: string) {
  const po = db.purchaseOrders.find(item => item.id === id)

  if (!po)
    throw new FlowError(`找不到采购单: ${id}`)

  return po
}

export function submitPurchaseOrder(db: MockDatabase, id: string, actor: Actor): PurchaseOrder {
  requireActorPermission(actor, 'purchase_order:submit')

  const po = findPo(db, id)

  if (po.status !== 'draft')
    throw new FlowError('只有草稿采购单可以提交')

  po.status = 'submitted'
  po.submittedById = actor.userId

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
  requireActorPermission(actor, 'purchase_order:approve')

  const po = findPo(db, id)

  if (po.status !== 'submitted')
    throw new FlowError('只有待审批采购单可以通过')

  if (po.submittedById === actor.userId)
    throw new FlowError('采购单提交人不能批准自己的采购单')

  po.status = 'approved'

  const approval = db.approvals.find(item => item.targetType === 'purchase_order' && item.targetId === po.id && item.status === 'pending')

  if (approval)
    approval.status = 'approved'

  writeAudit(db, actor, 'approve', 'purchase_order', po.id, `批准采购单 ${po.no}`)

  return po
}

export function rejectPurchaseOrder(db: MockDatabase, id: string, actor: Actor): PurchaseOrder {
  requireActorPermission(actor, 'purchase_order:approve')

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
  requireActorPermission(actor, 'purchase_receipt:submit')

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

export interface PurchaseLineDraft {
  internalSku: string
  qty: number
  unitCost: string
}

export interface PurchaseDraft {
  supplierId: string
  expectedAt: string
  lines: PurchaseLineDraft[]
  submit: boolean
  sourceSuggestionId?: string
}

export interface SupplierDraft {
  id?: string
  name: string
  country: string
  currency: CurrencyCode
  remark: string
  contactName: string
  email: string
  phone: string
}

export interface PurchaseReturnDraft {
  supplierId: string
  purchaseOrderId: string
  amount: string
  lines?: Array<{ internalSku: string; warehouseId?: string; batchNo?: string; qty: number }>
}

const currencies = new Set<CurrencyCode>(['USD', 'CNY', 'EUR', 'GBP', 'JPY'])

function expectedAtOf(value: string) {
  const text = value.trim()

  if (/^\d{4}-\d{2}-\d{2}$/.test(text))
    return `${text}T00:00:00.000Z`

  if (text.includes('T'))
    return text

  throw new FlowError('交期格式应为 YYYY-MM-DD')
}

export function createPurchaseOrder(db: MockDatabase, input: PurchaseDraft, actor: Actor): PurchaseOrder {
  requireActorPermission(actor, 'purchase_order:create')

  const supplier = mustFind(db.suppliers, input.supplierId, '供应商')

  if (supplier.status !== 'active')
    throw new FlowError('供应商已暂停，不能新建采购单')

  if (input.lines.length === 0)
    throw new FlowError('请至少添加一行货品')

  const id = nextId(db, 'po')

  const po: PurchaseOrder = {
    id,
    no: `PO-2026-${String(db.purchaseOrders.length + 1).padStart(3, '0')}`,
    supplierId: supplier.id,
    status: 'draft',
    currency: supplier.currency,
    expectedAt: expectedAtOf(input.expectedAt),
    createdBy: actor.name,
    createdAt: actor.at,
    sourceSuggestionId: input.sourceSuggestionId,
  }

  db.purchaseOrders.push(po)

  for (const line of input.lines) {
    if (!Number.isInteger(line.qty) || line.qty <= 0)
      throw new FlowError('数量必须是正整数')

    const sku = db.skus.find(item => item.internalSku === line.internalSku)

    if (!sku)
      throw new FlowError(`找不到 SKU: ${line.internalSku}`)

    db.purchaseOrderLines.push({
      id: nextId(db, 'pol'),
      purchaseOrderId: id,
      internalSku: line.internalSku,
      qty: line.qty,
      receivedQty: 0,
      unitCost: minorFromDecimal(line.unitCost),
      currency: supplier.currency,
    })
  }

  writeAudit(db, actor, 'create', 'purchase_order', id, `新建采购单 ${po.no}`)

  if (input.submit)
    return submitPurchaseOrder(db, id, actor)

  return po
}

export function cancelPurchaseOrder(db: MockDatabase, id: string, actor: Actor): PurchaseOrder {
  requireActorPermission(actor, 'purchase_order:write')

  const po = findPo(db, id)

  if (po.status !== 'draft' && po.status !== 'rejected')
    throw new FlowError('只有草稿或已驳回的采购单可以作废')

  po.status = 'cancelled'
  writeAudit(db, actor, 'cancel', 'purchase_order', po.id, `作废采购单 ${po.no}`)

  return po
}

export function saveSupplier(db: MockDatabase, input: SupplierDraft, actor: Actor): Supplier {
  requireActorPermission(actor, input.id ? 'supplier:write' : 'supplier:create')

  const name = input.name.trim()

  if (!name)
    throw new FlowError('请填写供应商名称')

  if (!currencies.has(input.currency))
    throw new FlowError('结算币种不在支持范围内')

  if (input.id) {
    const current = mustFind(db.suppliers, input.id, '供应商')

    current.name = name
    current.country = input.country.trim() || current.country
    current.currency = input.currency
    current.remark = input.remark.trim()

    const contact = db.supplierContacts.find(item => item.supplierId === current.id)

    if (contact) {
      contact.name = input.contactName.trim() || contact.name
      contact.email = input.email.trim()
      contact.phone = input.phone.trim()
    }
    else {
      db.supplierContacts.push({
        id: nextId(db, 'sc'),
        supplierId: current.id,
        name: input.contactName.trim() || '采购联系人',
        email: input.email.trim(),
        phone: input.phone.trim(),
      })
    }

    writeAudit(db, actor, 'update', 'supplier', current.id, `修改供应商 ${current.name}`)

    return current
  }

  const created: Supplier = {
    id: nextId(db, 'sup'),
    name,
    country: input.country.trim() || 'CN',
    currency: input.currency,
    status: 'active',
    remark: input.remark.trim(),
  }

  db.suppliers.push(created)
  db.supplierContacts.push({
    id: nextId(db, 'sc'),
    supplierId: created.id,
    name: input.contactName.trim() || '采购联系人',
    email: input.email.trim(),
    phone: input.phone.trim(),
  })
  writeAudit(db, actor, 'create', 'supplier', created.id, `新建供应商 ${created.name}`)

  return created
}

export function setSupplierStatus(db: MockDatabase, ids: string[], status: 'active' | 'paused', actor: Actor) {
  requireActorPermission(actor, 'supplier:write')
  for (const id of ids) {
    const supplier = mustFind(db.suppliers, id, '供应商')

    supplier.status = status
    writeAudit(db, actor, status === 'active' ? 'enable' : 'pause', 'supplier', id, `${status === 'active' ? '恢复' : '暂停'}供应商 ${supplier.name}`)
  }
}

export function createPurchaseReturn(db: MockDatabase, input: PurchaseReturnDraft, actor: Actor): PurchaseReturn {
  requireActorPermission(actor, 'purchase_order:create')

  const supplier = db.suppliers.find(item => item.id === input.supplierId)

  if (!supplier)
    throw new FlowError(`找不到供应商: ${input.supplierId}`)

  const po = findPo(db, input.purchaseOrderId)

  if (po.supplierId !== supplier.id)
    throw new FlowError('采购单不属于这个供应商')

  if (!input.lines || input.lines.length === 0)
    throw new FlowError('退货明细不能为空')

  const lines = input.lines.map(line => ({
    internalSku: line.internalSku,
    warehouseId: line.warehouseId ?? '',
    batchNo: line.batchNo ?? '',
    qty: line.qty,
  }))

  if (lines.some(line => !Number.isInteger(line.qty) || line.qty <= 0))
    throw new FlowError('退货数量必须是正整数')

  const computedAmount = lines.reduce((sum, line) => {
    const poLine = db.purchaseOrderLines.find(item => item.purchaseOrderId === po.id && item.internalSku === line.internalSku)

    if (!poLine)
      throw new FlowError(`退货明细找不到采购行: ${line.internalSku}`)

    const returnedQty = db.purchaseReturns
      .filter(item => item.purchaseOrderId === po.id && item.status === 'confirmed')
      .flatMap(item => item.lines ?? [])
      .filter(returnLine => returnLine.internalSku === line.internalSku)
      .reduce((total, returnLine) => total + returnLine.qty, 0)

    const availableQty = poLine.receivedQty - returnedQty

    if (line.qty > availableQty)
      throw new FlowError(`${line.internalSku} 退货数量超过已收货未退货数量（可退 ${availableQty} 件）`)

    return addMinor(sum, mulQty(poLine.unitCost, line.qty))
  }, 0)

  if (computedAmount <= 0)
    throw new FlowError('退货明细没有匹配采购成本')

  const row: PurchaseReturn = {
    id: nextId(db, 'prt'),
    no: `PR-2026-${String(db.purchaseReturns.length + 1).padStart(3, '0')}`,
    supplierId: supplier.id,
    purchaseOrderId: po.id,
    status: 'draft',
    currency: po.currency,
    amount: computedAmount,
    lines,
    payableReduction: computedAmount,
  }

  db.purchaseReturns.push(row)
  writeAudit(db, actor, 'create', 'purchase_return', row.id, `新建采购退货 ${row.no}。确认前不改库存。`)

  return row
}

export function confirmPurchaseReturn(db: MockDatabase, id: string, actor: Actor): PurchaseReturn {
  requireActorPermission(actor, 'purchase_order:write')

  const row = db.purchaseReturns.find(item => item.id === id)

  if (!row)
    throw new FlowError(`找不到采购退货: ${id}`)

  if (row.status !== 'draft')
    throw new FlowError('只有草稿采购退货可以确认')

  const lines = row.lines ?? []
  if (lines.length === 0)
    throw new FlowError('退货缺少明细行，不能确认')
  for (const line of lines) {
    applyMovement(db, {
      warehouseId: line.warehouseId,
      internalSku: line.internalSku,
      onHandDelta: -line.qty,
      inTransitDelta: 0,
      reason: 'purchase_return',
      refType: 'purchase_return',
      refId: row.id,
      actor,
    })

    const poLine = db.purchaseOrderLines.find(item => item.purchaseOrderId === row.purchaseOrderId && item.internalSku === line.internalSku)

    if (!poLine)
      throw new FlowError(`退货明细找不到采购行: ${line.internalSku}`)

    poLine.receivedQty -= line.qty
  }

  const invoice = db.apInvoices.find(item => item.purchaseOrderId === row.purchaseOrderId && item.supplierId === row.supplierId && item.status === 'open')

  if (!invoice) {
    writeAudit(db, actor, 'pending_difference', 'purchase_return', row.id, `待处理应付差异：采购单 ${row.purchaseOrderId} 没有关联的未结应付发票，未冲减应付`)
  }
  else if (invoice.amount < row.amount) {
    const difference = row.amount - invoice.amount

    invoice.amount = 0
    writeAudit(db, actor, 'pending_difference', 'purchase_return', row.id, `待处理应付差异：关联发票金额不足 ${minorToDecimal(difference)}`)
  }
  else {
    invoice.amount -= row.amount
  }

  row.status = 'confirmed'
  row.payableReduction = row.amount
  writeAudit(db, actor, 'confirm', 'purchase_return', row.id, `确认采购退货 ${row.no}，${lines.map(line => `${line.internalSku} -${line.qty}`).join('；')}，库存与应付已同步冲减`)

  return row
}

export function generateStatement(db: MockDatabase, supplierId: string, period: string, actor: Actor): SupplierStatement {
  requireActorPermission(actor, 'supplier:create')

  const supplier = mustFind(db.suppliers, supplierId, '供应商')

  if (!/^\d{4}-\d{2}$/.test(period))
    throw new FlowError('期间格式应为 YYYY-MM')

  const orders = db.purchaseOrders.filter(item => item.supplierId === supplier.id && item.expectedAt.slice(0, 7) === period)
  let amount = 0

  for (const order of orders) {
    for (const line of db.purchaseOrderLines.filter(item => item.purchaseOrderId === order.id))
      amount = addMinor(amount, mulQty(line.unitCost, line.qty))
  }

  const row: SupplierStatement = {
    id: nextId(db, 'stm'),
    no: `ST-${period}-${String(db.statements.length + 1).padStart(2, '0')}`,
    supplierId: supplier.id,
    period,
    status: 'draft',
    currency: supplier.currency,
    amount,
  }

  db.statements.push(row)
  writeAudit(db, actor, 'create', 'supplier_statement', row.id, `生成对账单 ${row.no}，金额是该期间采购行的合计，不是付款。`)

  return row
}

export function submitStatement(db: MockDatabase, id: string, actor: Actor): SupplierStatement {
  requireActorPermission(actor, 'supplier:write')

  const row = mustFind(db.statements, id, '对账单')

  if (row.status !== 'draft')
    throw new FlowError('只有草稿对账单可以提交')

  row.status = 'submitted'
  db.approvals.push({
    id: nextId(db, 'apr'),
    targetType: 'supplier_statement',
    targetId: row.id,
    title: `供应商对账 ${row.no} 待审批`,
    type: '供应商对账',
    submitter: actor.name,
    submittedAt: actor.at,
    amount: row.amount,
    currency: row.currency,
    status: 'pending',
    summary: '对账单提交财务审批。这里不生成凭证，也不改应付余额。',
    storeId: null,
    lines: [
      { account: '应付账款', debit: 0, credit: row.amount },
      { account: '在途物资', debit: row.amount, credit: 0 },
    ],
  })
  writeAudit(db, actor, 'submit', 'supplier_statement', row.id, `提交对账单 ${row.no}，等待财务审批，未写账`)

  return row
}
