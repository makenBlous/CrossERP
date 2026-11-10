import { assertPermission, database, delay } from '@/api/mock-client'
import { createPurchaseOrder } from '@/mocks/services/procurement'
import { writeAudit } from '@/mocks/services/audit'
import { FlowError } from '@/mocks/services/errors'
import type {
  ReplenishmentDemandFactor,
  ReplenishmentDemandSnapshot,
  ReplenishmentLineType,
  ReplenishmentPlan,
  ReplenishmentPlanLine,
  ReplenishmentPlanSummary,
  ReplenishmentState,
  ReplenishmentSupplyBucket,
} from '@/types/replenishment'

const STORAGE_KEY = 'crosserp-replenishment-v1'
const STATE_VERSION = 1
const SCALE = 10000

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function simpleHash(value: string) {
  let hash = 0
  for (let index = 0; index < value.length; index += 1)
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0

  return `fnv-demo-${hash.toString(16).padStart(8, '0')}`
}

function factorLabel(num: number, den: number) {
  return `${(num / den).toFixed(2)}x`
}

function now() {
  return new Date().toISOString()
}

function activeFactor(factors: ReplenishmentDemandFactor[], sku: string, kind: 'season' | 'promo') {
  return factors.find(item => item.internalSku === sku && item.kind === kind && item.status === 'active')
}

function proposedFactor(factors: ReplenishmentDemandFactor[], sku: string) {
  return factors.find(item => item.internalSku === sku && item.status === 'proposed')
}

function buildSupply(overrides: Partial<Record<string, number>> = {}): ReplenishmentSupplyBucket[] {
  const base = [
    ['on_hand', '可售现货', 18, '2026-11-11', 'balance', 'bal-fba-us'],
    ['reserved', '已付款未发货预留', 3, '2026-11-11', 'reservation', 'res-2026-11'],
    ['pending_inspection', '待检', 4, '2026-11-13', 'receipt', 'receipt-2026-1109'],
    ['po_in_transit', '采购在途', 10, '2026-11-23', 'purchase_order', 'PO-2026-004'],
    ['first_mile_in_transit', '头程在途', 8, '2026-11-28', 'shipment', 'FM-2026-004'],
    ['transfer_in_transit', '调拨在途', 0, '2026-11-30', 'stock_transfer', 'TR-2026-001'],
    ['po_open', '已下单未发', 12, '2026-11-29', 'purchase_order', 'PO-2026-011'],
    ['shipment_open', '未完成发货计划', 2, '2026-11-26', 'ship_plan', 'SHP-PLAN-001'],
  ] as const

  return base.map(([bucket, label, qty, etaDate, refType, refId]) => ({
    bucket,
    label,
    qty: overrides[bucket] ?? qty,
    etaDate,
    refType,
    refId,
  }))
}

function demandSnapshot(sku: string, factors: ReplenishmentDemandFactor[], channel: 'sea' | 'air'): ReplenishmentDemandSnapshot {
  const weights = sku.endsWith('MAT-OLV') ? { w7: 7000, w14: 2000, w30: 1000 } : { w7: 5000, w14: 3000, w30: 2000 }
  const avg7 = sku.endsWith('MAT-OLV') ? 32000 : 22000
  const avg14 = sku.endsWith('MAT-OLV') ? 28000 : 20000
  const avg30 = sku.endsWith('MAT-OLV') ? 24000 : 18000
  const weighted = Math.round((weights.w7 * avg7 + weights.w14 * avg14 + weights.w30 * avg30) / SCALE)
  const season = activeFactor(factors, sku, 'season') ?? { num: 1, den: 1 }
  const promo = activeFactor(factors, sku, 'promo') ?? { num: 1, den: 1 }
  const dailyScaled = Math.round((weighted * season.num * promo.num) / (season.den * promo.den))
  const safetyDays = sku.endsWith('MAT-OLV') ? 10 : 14
  const safetyQty = Math.round(dailyScaled * safetyDays / SCALE)
  const leadDays = channel === 'sea' ? 47 : 25

  return {
    avg7,
    avg14,
    avg30,
    validDays30: 20,
    stockoutDays30: 10,
    dailyScaled,
    safetyDays,
    safetyQty,
    leadDays,
    horizonDays: leadDays + safetyDays + 7,
    weights,
    seasonNum: season.num,
    seasonDen: season.den,
    promoNum: promo.num,
    promoDen: promo.den,
    factorStatus: proposedFactor(factors, sku) ? 'proposed' : 'active',
  }
}

function makeLine(
  planId: string,
  lineIndex: number,
  sku: string,
  skuTitle: string,
  lineType: ReplenishmentLineType,
  factors: ReplenishmentDemandFactor[],
  previous?: ReplenishmentPlanLine,
): ReplenishmentPlanLine {
  const channel = lineType === 'ship_fba' ? 'sea' : sku.endsWith('MAT-OLV') ? 'air' : 'sea'
  const demand = demandSnapshot(sku, factors, channel)
  const isMat = sku.endsWith('MAT-OLV')
  const rawQty = lineType === 'ship_fba' ? 70 : isMat ? 16 : 57
  const suggestedQty = lineType === 'ship_fba' ? 27 : isMat ? 18 : 48
  const supply = lineType === 'ship_fba' ? buildSupply({ on_hand: 18, reserved: 2, po_in_transit: 10, first_mile_in_transit: 8, po_open: 0 }) : buildSupply()
  const frozen = previous?.frozen ?? false
  const shownQty = frozen ? previous?.suggestedQty ?? suggestedQty : suggestedQty

  return {
    id: `${planId}-line-${lineIndex}`,
    planId,
    internalSku: sku,
    skuTitle,
    warehouseId: lineType === 'ship_fba' ? 'wh-cn-sz' : 'wh-fba-us',
    warehouseName: lineType === 'ship_fba' ? '深圳备货仓' : '亚马逊 FBA 美国',
    lineType,
    channel,
    rawQty,
    suggestedQty: shownQty,
    frozen,
    prevQty: previous?.suggestedQty ?? null,
    deltaQty: previous ? shownQty - previous.suggestedQty : shownQty,
    mustStockoutQty: lineType === 'ship_fba' ? 2 : 0,
    cappedBy: lineType === 'buy' && !isMat ? ['最大采购量（48 件）'] : [],
    belowMoq: false,
    forecastStatus: 'ready',
    unitPriceMinor: lineType === 'buy' ? (isMat ? 360000 : 1860000) : null,
    currency: 'CNY',
    availableOnHand: lineType === 'ship_fba' ? 27 : 18,
    reservedQty: lineType === 'ship_fba' ? 2 : 3,
    pendingInspectionQty: 4,
    inTransitQty: 18,
    poOpenQty: lineType === 'ship_fba' ? 0 : 12,
    shipmentOpenQty: lineType === 'ship_fba' ? 2 : 0,
    supply,
    demand,
    cartonSize: lineType === 'buy' ? 6 : 1,
    moq: lineType === 'buy' ? (isMat ? 12 : 24) : 0,
    maxPurchaseQty: lineType === 'buy' ? (isMat ? 60 : 48) : 0,
    capitalCapMinor: lineType === 'buy' ? 120000000 : 0,
  }
}

function defaultFactors(): ReplenishmentDemandFactor[] {
  return [
    { id: 'factor-season-tent', internalSku: 'NW-TENT-2P-OLV', kind: 'season', num: 1, den: 1, status: 'active', origin: 'manual', proposedById: 'demo-operations-manager', proposedByName: '演示运营主管' },
    { id: 'factor-promo-tent', internalSku: 'NW-TENT-2P-OLV', kind: 'promo', num: 1, den: 1, status: 'active', origin: 'manual', proposedById: 'demo-operations-manager', proposedByName: '演示运营主管' },
    { id: 'factor-season-mat', internalSku: 'NW-MAT-OLV', kind: 'season', num: 1, den: 1, status: 'active', origin: 'manual', proposedById: 'demo-operations-manager', proposedByName: '演示运营主管' },
    { id: 'factor-promo-mat', internalSku: 'NW-MAT-OLV', kind: 'promo', num: 1, den: 1, status: 'active', origin: 'manual', proposedById: 'demo-operations-manager', proposedByName: '演示运营主管' },
    { id: 'factor-ai-tent', internalSku: 'NW-TENT-2P-OLV', kind: 'season', num: 3, den: 2, status: 'proposed', origin: 'ai', proposedById: 'agent:replenishment-assistant', proposedByName: '补货助手' },
  ]
}

function defaultPlans(factors: ReplenishmentDemandFactor[]): ReplenishmentPlan[] {
  const oldId = 'rp-2026-11-09-v2'
  const currentId = 'rp-2026-11-11-v3'

  const oldLines = [
    makeLine(oldId, 1, 'NW-TENT-2P-OLV', '双人帐篷 橄榄绿', 'buy', factors),
    makeLine(oldId, 2, 'NW-TENT-2P-OLV', '双人帐篷 橄榄绿', 'ship_fba', factors),
    makeLine(oldId, 3, 'NW-MAT-OLV', '防潮垫 橄榄绿', 'buy', factors),
  ]

  oldLines[0].suggestedQty = 42
  oldLines[0].deltaQty = 42
  oldLines[1].suggestedQty = 24
  oldLines[1].deltaQty = 24

  const currentLines = oldLines.map((line, index) => makeLine(currentId, index + 1, line.internalSku, line.skuTitle, line.lineType, factors, index === 0 ? { ...line, frozen: true } : undefined))

  currentLines[0].frozen = true
  currentLines[0].suggestedQty = 42
  currentLines[0].prevQty = 42
  currentLines[0].deltaQty = 0
  currentLines[1].prevQty = 24
  currentLines[1].deltaQty = 3
  currentLines[2].prevQty = 16
  currentLines[2].deltaQty = 2

  return [
    { id: oldId, versionNo: 2, runAt: '2026-11-09T08:30:00.000Z', runBy: '演示采购', methodVersion: 'replenishment-v1.0', weightVersion: 'w7/w14/w30-50/30/20', status: 'superseded', inputsHash: simpleHash(JSON.stringify(oldLines)), lines: oldLines, note: '上一版本：未冻结行可被新版本替代。' },
    { id: currentId, versionNo: 3, runAt: '2026-11-11T08:30:00.000Z', runBy: '演示采购', methodVersion: 'replenishment-v1.0', weightVersion: 'w7/w14/w30-50/30/20', status: 'partially_confirmed', inputsHash: simpleHash(JSON.stringify(currentLines)), lines: currentLines, note: '演示数据；金额和数量由确定性代码生成。' },
  ]
}

function loadState(): ReplenishmentState {
  if (typeof localStorage !== 'undefined') {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '') as ReplenishmentState
      if (parsed.version === STATE_VERSION && Array.isArray(parsed.plans) && Array.isArray(parsed.factors))
        return parsed
    }
    catch {
      // 损坏的补货演示缓存回退到固定种子。
    }
  }
  const factors = defaultFactors()
  const value = { version: STATE_VERSION, plans: defaultPlans(factors), factors }

  persistState(value)

  return value
}

function persistState(state: ReplenishmentState) {
  if (typeof localStorage !== 'undefined')
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

function latest(state: ReplenishmentState) {
  return [...state.plans].sort((a, b) => b.versionNo - a.versionNo)[0]
}

function summary(plan: ReplenishmentPlan): ReplenishmentPlanSummary {
  return {
    id: plan.id,
    versionNo: plan.versionNo,
    runAt: plan.runAt,
    runBy: plan.runBy,
    methodVersion: plan.methodVersion,
    weightVersion: plan.weightVersion,
    status: plan.status,
    inputsHash: plan.inputsHash,
    note: plan.note,
    lineCount: plan.lines.length,
    frozenCount: plan.lines.filter(line => line.frozen).length,
    suggestedQty: plan.lines.reduce((sum, line) => sum + line.suggestedQty, 0),
    mustStockoutQty: plan.lines.reduce((sum, line) => sum + line.mustStockoutQty, 0),
  }
}

export function listReplenishmentPlans(): ReplenishmentPlanSummary[] {
  const state = loadState()

  return state.plans
    .slice()
    .sort((a, b) => b.versionNo - a.versionNo)
    .map(summary)
}

export function getReplenishmentPlan(id: string): ReplenishmentPlan | undefined {
  return clone(loadState().plans.find(plan => plan.id === id))
}

export function getLatestReplenishmentPlan(): ReplenishmentPlan {
  return clone(latest(loadState()))
}

export function getReplenishmentFactors(sku?: string) {
  return clone(loadState().factors.filter(item => !sku || item.internalSku === sku))
}

export function runReplenishmentPlan() {
  const actor = assertPermission('material_request:create')
  const state = loadState()
  const previous = latest(state)
  const versionNo = previous.versionNo + 1
  const id = `rp-2026-11-11-v${versionNo}`
  const previousByKey = new Map(previous.lines.map(line => [`${line.internalSku}:${line.lineType}`, line]))

  const configs: Array<[string, string, ReplenishmentLineType]> = [
    ['NW-TENT-2P-OLV', '双人帐篷 橄榄绿', 'buy'],
    ['NW-TENT-2P-OLV', '双人帐篷 橄榄绿', 'ship_fba'],
    ['NW-MAT-OLV', '防潮垫 橄榄绿', 'buy'],
  ]

  const lines = configs.map(([sku, title, type], index) => makeLine(id, index + 1, sku, title, type, state.factors, previousByKey.get(`${sku}:${type}`)))

  const plan: ReplenishmentPlan = {
    id,
    versionNo,
    runAt: now(),
    runBy: actor.name,
    methodVersion: 'replenishment-v1.0',
    weightVersion: 'w7/w14/w30-50/30/20',
    status: lines.some(line => line.frozen) ? 'partially_confirmed' : 'calculated',
    inputsHash: simpleHash(JSON.stringify(lines)),
    lines,
    note: '新版本已生成；冻结行沿用上一版数量，未冻结行重新计算。',
  }

  previous.status = 'superseded'
  state.plans.push(plan)
  persistState(state)
  writeAudit(database().db, actor, 'run', 'replenishment_plan', id, `运行补货计划 V${versionNo}，生成 ${lines.length} 行；冻结行不覆盖`)
  database().persist()

  return clone(plan)
}

export function setReplenishmentFreeze(planId: string, lineId: string, frozen: boolean) {
  const actor = assertPermission('material_request:write')
  const state = loadState()
  const plan = state.plans.find(item => item.id === planId)
  const line = plan?.lines.find(item => item.id === lineId)
  if (!plan || !line)
    throw new FlowError('找不到补货计划行')
  if (line.convertedDraftId && !frozen)
    throw new FlowError('已生成采购申请草稿的行不能解冻')
  line.frozen = frozen
  plan.status = plan.lines.every(item => item.frozen || item.suggestedQty === 0) ? 'confirmed' : 'partially_confirmed'
  persistState(state)
  writeAudit(database().db, actor, frozen ? 'freeze' : 'unfreeze', 'replenishment_plan_line', line.id, `${frozen ? '冻结' : '解冻'} ${line.internalSku} ${line.lineType}，建议 ${line.suggestedQty} 件`)
  database().persist()

  return clone(line)
}

export function convertReplenishmentLine(planId: string, lineId: string) {
  const actor = assertPermission('material_request:submit')
  const state = loadState()
  const plan = state.plans.find(item => item.id === planId)
  const line = plan?.lines.find(item => item.id === lineId)
  if (!plan || !line)
    throw new FlowError('找不到补货计划行')
  if (!line.frozen)
    throw new FlowError('请先冻结确认计划行，再生成采购申请草稿')
  if (line.lineType !== 'buy')
    throw new FlowError('发货建议请在物流计划中生成发货草稿')
  if (line.convertedDraftId)
    throw new FlowError('该行已经生成采购申请草稿，不能重复生成')

  const db = database()
  const supplier = db.db.suppliers.find(item => item.status === 'active')
  if (!supplier)
    throw new FlowError('没有可用供应商')

  const purchase = createPurchaseOrder(db.db, {
    supplierId: supplier.id,
    expectedAt: '2026-12-20',
    sourceSuggestionId: line.id,
    lines: [{ internalSku: line.internalSku, qty: line.suggestedQty, unitCost: '186.0000' }],
    submit: false,
  }, actor)

  line.convertedDraftId = purchase.id
  line.sourceSuggestionId = line.id
  line.convertedAt = actor.at
  if (plan.lines.every(item => item.convertedDraftId || item.lineType !== 'buy' || item.suggestedQty === 0))
    plan.status = 'converted'
  persistState(state)
  db.persist()
  writeAudit(db.db, actor, 'convert', 'purchase_order', purchase.id, `从补货计划 ${plan.id} 生成采购申请草稿，source_suggestion_id=${line.id}`)
  db.persist()

  return { purchase, line: clone(line) }
}

function parseFactor(value: string) {
  const text = value.trim()
  if (!/^\d+(?:\.\d{1,2})?$/.test(text))
    throw new FlowError('系数请输入正数，最多两位小数')
  const [whole, fraction = ''] = text.split('.')
  const den = 10 ** fraction.length
  const num = Number(whole) * den + Number(fraction || 0)
  if (!Number.isInteger(num) || num <= 0 || num > 1000)
    throw new FlowError('系数必须在 0 到 100 之间')

  return { num, den }
}

export function proposeDemandFactor(internalSku: string, kind: 'season' | 'promo', value: string, origin: 'ai' | 'manual' = 'manual') {
  const actor = assertPermission('material_request:write')
  const state = loadState()
  const parsed = parseFactor(value)
  const existing = state.factors.find(item => item.internalSku === internalSku && item.kind === kind && item.status === 'proposed')

  const factor: ReplenishmentDemandFactor = existing ?? {
    id: `factor-${internalSku}-${kind}-${Date.now()}`,
    internalSku,
    kind,
    num: parsed.num,
    den: parsed.den,
    status: 'proposed',
    origin,
    proposedById: actor.userId,
    proposedByName: actor.name,
  }

  factor.num = parsed.num
  factor.den = parsed.den
  factor.status = 'proposed'
  factor.origin = origin
  factor.proposedById = actor.userId
  factor.proposedByName = actor.name
  if (!existing)
    state.factors.push(factor)
  persistState(state)
  writeAudit(database().db, actor, 'propose', 'demand_factor', factor.id, `${origin === 'ai' ? 'AI' : '人工'}建议 ${internalSku} ${kind} 系数 ${factorLabel(factor.num, factor.den)}，待运营主管审批`)
  database().persist()

  return clone(factor)
}

export function approveDemandFactor(factorId: string) {
  const actor = assertPermission('material_request:approve')
  const state = loadState()
  const factor = state.factors.find(item => item.id === factorId)
  if (!factor)
    throw new FlowError('找不到需求系数建议')
  if (factor.status !== 'proposed')
    throw new FlowError('只有待审批的需求系数可以批准')
  if (factor.proposedById === actor.userId)
    throw new FlowError('需求系数建议人不能批准自己的建议')
  factor.status = 'active'
  factor.approvedById = actor.userId
  factor.approvedAt = actor.at
  persistState(state)
  writeAudit(database().db, actor, 'approve', 'demand_factor', factor.id, `批准 ${factor.internalSku} ${factor.kind} 系数 ${factorLabel(factor.num, factor.den)}；下次运行才生效`)
  database().persist()

  return clone(factor)
}

export function formatDemandFactor(num: number, den: number) {
  return factorLabel(num, den)
}

export async function fetchReplenishmentPlans() {
  await delay()
  assertPermission('material_request:read')

  return listReplenishmentPlans()
}

export async function fetchReplenishmentPlan(id: string) {
  await delay()
  assertPermission('material_request:read')

  return getReplenishmentPlan(id)
}

export async function fetchLatestReplenishmentPlan() {
  await delay()
  assertPermission('material_request:read')

  return getLatestReplenishmentPlan()
}
