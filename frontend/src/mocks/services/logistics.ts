import type { CurrencyCode } from '@/types/domain'
import type { Actor, Carrier, FreightCheck, MockDatabase, Shipment, ShippingRate } from '@/types/entities'
import { writeAudit } from '@/mocks/services/audit'
import { FlowError } from '@/mocks/services/errors'
import { mustFind, nextId } from '@/mocks/services/ids'
import { requireActorPermission } from '@/utils/service-permissions'
import { applyMovement, postStockDoc } from '@/mocks/services/inventory'
import { minorFromDecimal } from '@/utils/money'

function findShipment(db: MockDatabase, id: string) {
  return mustFind(db.shipments, id, '头程运单')
}

export function departShipment(db: MockDatabase, id: string, actor: Actor): Shipment {
  requireActorPermission(actor, 'shipment:write')

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
  requireActorPermission(actor, 'shipment:write')

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

export interface ShipmentDraft {
  carrierId: string
  warehouseFrom: string
  warehouseTo: string
  internalSku: string
  qty: number
  containerNo: string
  volumetricKg: string
  chargeAmount: string
}

export interface ShipmentFeeDraft {
  shipmentId: string
  chargeType: string
  amount: string
  currency: CurrencyCode
  containerNo: string
  volumetricKg: string
}

export interface CarrierDraft {
  id?: string
  name: string
}

export interface RateDraft {
  id?: string
  carrierId: string
  dest: string
  unit: string
  price: string
  currency: CurrencyCode
  validFrom: string
}

function requireActiveWarehouse(db: MockDatabase, id: string, label: string) {
  const warehouse = mustFind(db.warehouses, id, label)

  if (!warehouse.active)
    throw new FlowError(`${label}已停用`)

  return warehouse
}

export function createShipment(db: MockDatabase, input: ShipmentDraft, actor: Actor): Shipment {
  requireActorPermission(actor, 'shipment:create')

  const carrier = mustFind(db.carriers, input.carrierId, '物流商')

  if (!carrier.active)
    throw new FlowError('物流商已停用')

  const from = requireActiveWarehouse(db, input.warehouseFrom, '始发仓')
  const to = requireActiveWarehouse(db, input.warehouseTo, '目的仓')

  if (from.id === to.id)
    throw new FlowError('始发仓和目的仓不能相同')

  if (!Number.isInteger(input.qty) || input.qty <= 0)
    throw new FlowError('数量必须是正整数')

  const sku = db.skus.find(item => item.internalSku === input.internalSku)

  if (!sku)
    throw new FlowError(`找不到 SKU: ${input.internalSku}`)

  const id = nextId(db, 'shp')

  const shipment: Shipment = {
    id,
    no: `FM-2026-${String(db.shipments.length + 1).padStart(3, '0')}`,
    carrierId: carrier.id,
    warehouseFrom: from.id,
    warehouseTo: to.id,
    status: 'planned',
    departedAt: null,
    arrivedAt: null,
    containerNo: input.containerNo.trim(),
    volumetricKg: input.volumetricKg.trim(),
  }

  db.shipments.push(shipment)
  db.shipmentLines.push({
    id: nextId(db, 'spl'),
    shipmentId: id,
    internalSku: input.internalSku,
    qty: input.qty,
  })

  const charge = input.chargeAmount.trim()

  if (charge) {
    db.shipmentCharges.push({
      id: nextId(db, 'chg'),
      shipmentId: id,
      chargeType: 'freight',
      amount: minorFromDecimal(charge),
      currency: 'CNY',
    })
  }

  writeAudit(db, actor, 'create', 'shipment', id, `新建头程计划 ${shipment.no}。发运前不改库存。`)

  return shipment
}

export function saveShipmentFee(db: MockDatabase, input: ShipmentFeeDraft, actor: Actor): Shipment {
  requireActorPermission(actor, 'shipment:write')

  const shipment = findShipment(db, input.shipmentId)
  const chargeType = input.chargeType.trim() || 'freight'

  shipment.containerNo = input.containerNo.trim()
  shipment.volumetricKg = input.volumetricKg.trim()
  db.shipmentCharges.push({
    id: nextId(db, 'chg'),
    shipmentId: shipment.id,
    chargeType,
    amount: minorFromDecimal(input.amount),
    currency: input.currency,
  })
  writeAudit(db, actor, 'update', 'shipment', shipment.id, `录入头程费用 ${shipment.no}。费用由人填写，页面不摊进利润。`)

  return shipment
}

export function saveCarrier(db: MockDatabase, input: CarrierDraft, actor: Actor): Carrier {
  requireActorPermission(actor, input.id ? 'shipment:write' : 'shipment:create')

  const name = input.name.trim()

  if (!name)
    throw new FlowError('请填写物流商名称')

  if (input.id) {
    const current = mustFind(db.carriers, input.id, '物流商')

    current.name = name
    writeAudit(db, actor, 'update', 'carrier', current.id, `修改物流商 ${current.name}`)

    return current
  }

  const created: Carrier = { id: nextId(db, 'car'), name, active: true }

  db.carriers.push(created)
  writeAudit(db, actor, 'create', 'carrier', created.id, `新建物流商 ${created.name}`)

  return created
}

export function setCarrierActive(db: MockDatabase, ids: string[], active: boolean, actor: Actor) {
  requireActorPermission(actor, 'shipment:write')
  for (const id of ids) {
    const carrier = mustFind(db.carriers, id, '物流商')

    carrier.active = active
    writeAudit(db, actor, active ? 'enable' : 'disable', 'carrier', id, `${active ? '启用' : '停用'}物流商 ${carrier.name}`)
  }
}

export function saveRateCard(db: MockDatabase, input: RateDraft, actor: Actor): ShippingRate {
  requireActorPermission(actor, input.id ? 'shipment:write' : 'shipment:create')
  mustFind(db.carriers, input.carrierId, '物流商')

  const validFrom = input.validFrom.trim()

  if (!/^\d{4}-\d{2}-\d{2}$/.test(validFrom))
    throw new FlowError('生效日格式应为 YYYY-MM-DD')

  if (input.id) {
    const current = mustFind(db.rateCards, input.id, '运费模板')

    current.carrierId = input.carrierId
    current.dest = input.dest.trim()
    current.unit = input.unit.trim() || 'kg'
    current.price = minorFromDecimal(input.price)
    current.currency = input.currency
    current.validFrom = validFrom
    writeAudit(db, actor, 'update', 'rate_card', current.id, `修改运费模板 ${current.dest}`)

    return current
  }

  const created: ShippingRate = {
    id: nextId(db, 'rate'),
    carrierId: input.carrierId,
    dest: input.dest.trim(),
    unit: input.unit.trim() || 'kg',
    price: minorFromDecimal(input.price),
    currency: input.currency,
    validFrom,
    validTo: null,
  }

  db.rateCards.push(created)
  writeAudit(db, actor, 'create', 'rate_card', created.id, `新建运费模板 ${created.dest}。这是预估报价，不替代账单。`)

  return created
}

export function submitFreightCheck(db: MockDatabase, id: string, actor: Actor): FreightCheck {
  requireActorPermission(actor, 'shipment:write')

  const check = mustFind(db.freightChecks, id, '物流费用核对')

  if (check.status === 'submitted')
    throw new FlowError('这张核对已经送审')

  if (check.variance === 0)
    throw new FlowError('没有差异，不用送审')

  const shipment = db.shipments.find(item => item.id === check.shipmentId)
  const amount = check.variance < 0 ? -check.variance : check.variance

  check.status = 'submitted'
  db.approvals.push({
    id: nextId(db, 'apr'),
    targetType: 'freight_check',
    targetId: check.id,
    title: `物流费用差异 ${shipment?.no ?? check.shipmentId}`,
    type: '物流费用',
    submitter: actor.name,
    submittedAt: actor.at,
    amount,
    currency: check.currency,
    status: 'pending',
    summary: '差异沿用已存储的账单减预估。未写凭证，也不改利润。',
    storeId: null,
    lines: [
      { account: '物流费用差异', debit: amount, credit: 0 },
      { account: '应付账款', debit: 0, credit: amount },
    ],
  })
  writeAudit(db, actor, 'submit', 'freight_check', check.id, `物流费用差异送审 ${shipment?.no ?? check.id}，未写账`)

  return check
}
