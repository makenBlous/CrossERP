import type { Actor, MockDatabase, StockDoc, Warehouse, WarehouseKind } from '@/types/entities'
import { writeAudit } from '@/mocks/services/audit'
import { FlowError } from '@/mocks/services/errors'
import { mustFind, nextId } from '@/mocks/services/ids'

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
    actorId: input.actor.userId,
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

export interface WarehouseDraft {
  id?: string
  code: string
  name: string
  kind: WarehouseKind
  country: string
}

export interface StockDocDraft {
  docType: 'inbound' | 'outbound' | 'transfer' | 'count'
  warehouseId: string
  toWarehouseId?: string
  internalSku: string
  qty: number
  qtyActual?: number
  remark: string
}

export interface CountActual {
  lineId: string
  qtyActual: number
}

function requireWarehouse(db: MockDatabase, id: string) {
  const warehouse = mustFind(db.warehouses, id, '仓库')

  if (!warehouse.active)
    throw new FlowError('仓库已停用')

  return warehouse
}

function requireQty(qty: number, label: string) {
  if (!Number.isInteger(qty) || qty <= 0)
    throw new FlowError(`${label}必须是正整数`)
}

export function saveWarehouse(db: MockDatabase, input: WarehouseDraft, actor: Actor): Warehouse {
  const code = input.code.trim()
  const name = input.name.trim()

  if (!code || !name)
    throw new FlowError('请填写仓库编码和名称')

  if (!['fba', 'overseas', 'domestic'].includes(input.kind))
    throw new FlowError('仓库类型只能是 FBA、海外仓或国内仓')

  const duplicated = db.warehouses.find(item => item.code === code && item.id !== input.id)

  if (duplicated)
    throw new FlowError('仓库编码已存在')

  if (input.id) {
    const current = mustFind(db.warehouses, input.id, '仓库')

    current.code = code
    current.name = name
    current.kind = input.kind
    current.country = input.country.trim() || current.country
    writeAudit(db, actor, 'update', 'warehouse', current.id, `修改仓库 ${current.code}`)

    return current
  }

  const created: Warehouse = {
    id: nextId(db, 'wh'),
    code,
    name,
    kind: input.kind,
    country: input.country.trim() || 'CN',
    storeId: null,
    active: true,
  }

  db.warehouses.push(created)
  writeAudit(db, actor, 'create', 'warehouse', created.id, `新建仓库 ${created.code}`)

  return created
}

export function setWarehouseActive(db: MockDatabase, ids: string[], active: boolean, actor: Actor) {
  for (const id of ids) {
    const warehouse = mustFind(db.warehouses, id, '仓库')

    warehouse.active = active
    writeAudit(db, actor, active ? 'enable' : 'disable', 'warehouse', id, `${active ? '启用' : '停用'}仓库 ${warehouse.code}`)
  }
}

export function createStockDoc(db: MockDatabase, input: StockDocDraft, actor: Actor): StockDoc {
  requireWarehouse(db, input.warehouseId)
  requireQty(input.qty, '数量')

  const sku = db.skus.find(item => item.internalSku === input.internalSku)

  if (!sku)
    throw new FlowError(`找不到 SKU: ${input.internalSku}`)

  if (input.docType === 'transfer') {
    if (!input.toWarehouseId)
      throw new FlowError('请选择调入仓')

    if (input.toWarehouseId === input.warehouseId)
      throw new FlowError('调出仓和调入仓不能相同')

    requireWarehouse(db, input.toWarehouseId)
  }

  const balance = db.balances.find(item => item.warehouseId === input.warehouseId && item.internalSku === input.internalSku)
  const book = balance?.onHand ?? 0
  const docId = nextId(db, 'doc')
  const prefix = { inbound: 'IN', outbound: 'OUT', transfer: 'TR', count: 'CT' }[input.docType]

  const actual = input.docType === 'count'
    ? (input.qtyActual ?? book)
    : 0

  if (input.docType === 'count' && (!Number.isInteger(actual) || actual < 0))
    throw new FlowError('实盘数量必须是非负整数')

  const doc: StockDoc = {
    id: docId,
    docNo: `${prefix}-${docId}`,
    docType: input.docType,
    warehouseId: input.warehouseId,
    toWarehouseId: input.docType === 'transfer' ? input.toWarehouseId ?? null : null,
    status: 'draft',
    remark: input.remark.trim() || '草稿，未过账，不改库存',
    createdBy: actor.name,
    createdAt: actor.at,
  }

  db.stockDocs.push(doc)
  db.stockDocLines.push({
    id: nextId(db, 'dln'),
    docId,
    internalSku: input.internalSku,
    qtyExpected: input.docType === 'count' ? book : input.qty,
    qtyActual: input.docType === 'count' ? actual : 0,
  })
  writeAudit(db, actor, 'create', 'stock_doc', docId, `新建${prefix}草稿 ${doc.docNo}`)

  return doc
}

export function postDraftStockDoc(db: MockDatabase, id: string, actor: Actor): StockDoc {
  const doc = mustFind(db.stockDocs, id, '库存单据')

  if (doc.status !== 'draft')
    throw new FlowError('只有草稿可以过账')

  if (doc.docType !== 'inbound' && doc.docType !== 'outbound')
    throw new FlowError('这张单据请用对应的过账动作')

  const lines = db.stockDocLines.filter(line => line.docId === doc.id)

  if (lines.length === 0)
    throw new FlowError('单据没有明细')

  for (const line of lines) {
    const qty = line.qtyExpected

    requireQty(qty, '数量')
    line.qtyActual = qty
    applyMovement(db, {
      warehouseId: doc.warehouseId,
      internalSku: line.internalSku,
      onHandDelta: doc.docType === 'inbound' ? qty : -qty,
      inTransitDelta: 0,
      reason: doc.docType,
      refType: 'stock_doc',
      refId: doc.id,
      actor,
    })
  }

  doc.status = 'posted'
  writeAudit(db, actor, doc.docType, 'stock_doc', doc.id, `${doc.docNo} 过账，库存已更新`)

  return doc
}

export function postTransfer(db: MockDatabase, id: string, actor: Actor): StockDoc {
  const doc = mustFind(db.stockDocs, id, '调拨单')

  if (doc.docType !== 'transfer')
    throw new FlowError('不是调拨单')

  if (doc.status !== 'draft')
    throw new FlowError('只有草稿调拨单可以确认')

  if (!doc.toWarehouseId)
    throw new FlowError('调拨单没有调入仓')

  const lines = db.stockDocLines.filter(line => line.docId === doc.id)

  if (lines.length === 0)
    throw new FlowError('调拨单没有明细')

  for (const line of lines) {
    requireQty(line.qtyExpected, '调拨数量')
    applyMovement(db, {
      warehouseId: doc.warehouseId,
      internalSku: line.internalSku,
      onHandDelta: -line.qtyExpected,
      inTransitDelta: 0,
      reason: 'transfer_out',
      refType: 'stock_doc',
      refId: doc.id,
      actor,
    })
    applyMovement(db, {
      warehouseId: doc.toWarehouseId,
      internalSku: line.internalSku,
      onHandDelta: line.qtyExpected,
      inTransitDelta: 0,
      reason: 'transfer_in',
      refType: 'stock_doc',
      refId: doc.id,
      actor,
    })
    line.qtyActual = line.qtyExpected
  }

  doc.status = 'posted'
  writeAudit(db, actor, 'transfer', 'stock_doc', doc.id, `${doc.docNo} 确认调拨，库存已从调出仓移到调入仓`)

  return doc
}

export function postStockCount(db: MockDatabase, id: string, actuals: CountActual[], actor: Actor): StockDoc {
  const doc = mustFind(db.stockDocs, id, '盘点单')

  if (doc.docType !== 'count')
    throw new FlowError('不是盘点单')

  if (doc.status !== 'draft')
    throw new FlowError('只有草稿盘点单可以过账')

  const lines = db.stockDocLines.filter(line => line.docId === doc.id)

  if (lines.length === 0)
    throw new FlowError('盘点单没有明细')

  for (const line of lines) {
    const edited = actuals.find(item => item.lineId === line.id)
    const actual = edited ? edited.qtyActual : line.qtyActual

    if (!Number.isInteger(actual) || actual < 0)
      throw new FlowError('实盘数量必须是非负整数')

    const balance = db.balances.find(item => item.warehouseId === doc.warehouseId && item.internalSku === line.internalSku)
    const book = balance?.onHand ?? 0

    line.qtyExpected = book
    line.qtyActual = actual

    const delta = actual - book

    if (delta !== 0) {
      applyMovement(db, {
        warehouseId: doc.warehouseId,
        internalSku: line.internalSku,
        onHandDelta: delta,
        inTransitDelta: 0,
        reason: delta > 0 ? 'count_gain' : 'count_loss',
        refType: 'stock_doc',
        refId: doc.id,
        actor,
      })
    }
  }

  doc.status = 'posted'
  writeAudit(db, actor, 'count', 'stock_doc', doc.id, `${doc.docNo} 差异过账。盘盈增加库存，盘亏减少库存。`)

  return doc
}
