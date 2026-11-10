export type ReplenishmentPlanStatus = 'calculated' | 'reviewed' | 'partially_confirmed' | 'confirmed' | 'converted' | 'superseded'
export type ReplenishmentLineType = 'buy' | 'ship_fba' | 'ship_overseas'
export type ReplenishmentFactorStatus = 'proposed' | 'active' | 'rejected'

export interface ReplenishmentSupplyBucket {
  bucket: string
  label: string
  qty: number
  etaDate: string
  refType: string
  refId: string
}

export interface ReplenishmentDemandSnapshot {
  avg7: number
  avg14: number
  avg30: number
  validDays30: number
  stockoutDays30: number
  dailyScaled: number
  safetyDays: number
  safetyQty: number
  leadDays: number
  horizonDays: number
  weights: { w7: number; w14: number; w30: number }
  seasonNum: number
  seasonDen: number
  promoNum: number
  promoDen: number
  factorStatus: ReplenishmentFactorStatus
}

export interface ReplenishmentPlanLine {
  id: string
  planId: string
  internalSku: string
  skuTitle: string
  warehouseId: string
  warehouseName: string
  lineType: ReplenishmentLineType
  channel: 'sea' | 'air'
  rawQty: number
  suggestedQty: number
  frozen: boolean
  prevQty: number | null
  deltaQty: number
  mustStockoutQty: number
  cappedBy: string[]
  belowMoq: boolean
  forecastStatus: 'ready' | 'forecast_missing'
  unitPriceMinor: number | null
  currency: 'CNY'
  availableOnHand: number
  reservedQty: number
  pendingInspectionQty: number
  inTransitQty: number
  poOpenQty: number
  shipmentOpenQty: number
  supply: ReplenishmentSupplyBucket[]
  demand: ReplenishmentDemandSnapshot
  cartonSize: number
  moq: number
  maxPurchaseQty: number
  capitalCapMinor: number
  sourceSuggestionId?: string
  convertedDraftId?: string
  convertedAt?: string
}

export interface ReplenishmentPlan {
  id: string
  versionNo: number
  runAt: string
  runBy: string
  methodVersion: string
  weightVersion: string
  status: ReplenishmentPlanStatus
  inputsHash: string
  lines: ReplenishmentPlanLine[]
  note: string
}

export interface ReplenishmentDemandFactor {
  id: string
  internalSku: string
  kind: 'season' | 'promo'
  num: number
  den: number
  status: ReplenishmentFactorStatus
  origin: 'ai' | 'manual'
  proposedById: string
  proposedByName: string
  approvedById?: string
  approvedAt?: string
}

export interface ReplenishmentState {
  version: number
  plans: ReplenishmentPlan[]
  factors: ReplenishmentDemandFactor[]
}

export interface ReplenishmentPlanSummary extends Omit<ReplenishmentPlan, 'lines'> {
  lineCount: number
  frozenCount: number
  suggestedQty: number
  mustStockoutQty: number
}
