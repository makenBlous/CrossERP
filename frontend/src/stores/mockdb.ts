import { defineStore } from 'pinia'
import { type SuggestionInput, decideApproval, submitSuggestion } from '@/mocks/services/approvals'
import {
  type BundleDraft,
  type CostDraft,
  type ListingDraft,
  type MappingDraft,
  type NamedDraft,
  type SkuDraft,
  addSkuCost,
  confirmMappings,
  removeBundles,
  saveBrand,
  saveBundle,
  saveCategory,
  saveListing,
  saveMapping,
  saveSku,
  setBrandActive,
  setCategoryActive,
  setListingStatus,
  setSkuActive,
} from '@/mocks/services/catalog'
import {
  type CountActual,
  type StockDocDraft,
  type WarehouseDraft,
  createStockDoc,
  postDraftStockDoc,
  postStockCount,
  postTransfer,
  saveWarehouse,
  setWarehouseActive,
} from '@/mocks/services/inventory'
import {
  type CarrierDraft,
  type RateDraft,
  type ShipmentDraft,
  type ShipmentFeeDraft,
  arriveShipment,
  createShipment,
  departShipment,
  saveCarrier,
  saveRateCard,
  saveShipmentFee,
  setCarrierActive,
  submitFreightCheck,
} from '@/mocks/services/logistics'
import { disposeReturn, registerReturn, shipSalesOrder } from '@/mocks/services/orders'
import {
  type PurchaseDraft,
  type PurchaseReturnDraft,
  type SupplierDraft,
  approvePurchaseOrder,
  cancelPurchaseOrder,
  confirmPurchaseReturn,
  createPurchaseOrder,
  createPurchaseReturn,
  generateStatement,
  receivePurchaseOrder,
  rejectPurchaseOrder,
  saveSupplier,
  setSupplierStatus,
  submitPurchaseOrder,
  submitStatement,
} from '@/mocks/services/procurement'
import { MOCK_DB_VERSION, buildSeed } from '@/mocks/seed/build'
import type { Actor, MockDatabase } from '@/types/entities'

const STORAGE_KEY = 'crosserp-mockdb-v1'

function isDatabase(value: unknown): value is MockDatabase {
  if (!value || typeof value !== 'object')
    return false

  const row = value as Partial<MockDatabase>

  return row.meta?.version === MOCK_DB_VERSION && Array.isArray(row.stores) && Array.isArray(row.orders) && Array.isArray(row.skus)
}

function loadDatabase(): MockDatabase {
  if (typeof localStorage === 'undefined')
    return buildSeed()

  try {
    const raw = localStorage.getItem(STORAGE_KEY)

    if (!raw)
      return buildSeed()

    const parsed: unknown = JSON.parse(raw)

    if (isDatabase(parsed))
      return parsed
  }
  catch {
    // 损坏的演示缓存直接丢弃，回到种子。
  }

  return buildSeed()
}

export const useMockDbStore = defineStore('mockdb', {
  state: () => ({
    db: loadDatabase(),
  }),
  actions: {
    persist() {
      if (typeof localStorage === 'undefined')
        return

      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.db))
      }
      catch {
        // 浏览器拒绝写入时保留内存数据。
      }
    },
    reset() {
      this.db = buildSeed()
      this.persist()
    },
    submitPurchase(id: string, actor: Actor) {
      const result = submitPurchaseOrder(this.db, id, actor)

      this.persist()

      return result
    },
    approvePurchase(id: string, actor: Actor) {
      const result = approvePurchaseOrder(this.db, id, actor)

      this.persist()

      return result
    },
    rejectPurchase(id: string, actor: Actor) {
      const result = rejectPurchaseOrder(this.db, id, actor)

      this.persist()

      return result
    },
    receivePurchase(id: string, warehouseId: string, actor: Actor) {
      const result = receivePurchaseOrder(this.db, id, warehouseId, actor)

      this.persist()

      return result
    },
    departFirstMile(id: string, actor: Actor) {
      const result = departShipment(this.db, id, actor)

      this.persist()

      return result
    },
    arriveFirstMile(id: string, actor: Actor) {
      const result = arriveShipment(this.db, id, actor)

      this.persist()

      return result
    },
    shipOrder(id: string, actor: Actor) {
      const result = shipSalesOrder(this.db, id, actor)

      this.persist()

      return result
    },
    suggest(input: SuggestionInput, actor: Actor) {
      const result = submitSuggestion(this.db, input, actor)

      this.persist()

      return result
    },
    decide(id: string, status: 'approved' | 'rejected', actor: Actor, comment = '') {
      const result = decideApproval(this.db, id, status, actor, comment)

      this.persist()

      return result
    },
    saveSku(input: SkuDraft & { id?: string }, actor: Actor) {
      const result = saveSku(this.db, input, actor)

      this.persist()

      return result
    },
    setSkuActive(ids: string[], active: boolean, actor: Actor) {
      setSkuActive(this.db, ids, active, actor)
      this.persist()
    },
    addSkuCost(input: CostDraft, actor: Actor) {
      const result = addSkuCost(this.db, input, actor)

      this.persist()

      return result
    },
    saveListing(input: ListingDraft, actor: Actor) {
      const result = saveListing(this.db, input, actor)

      this.persist()

      return result
    },
    setListingStatus(ids: string[], status: string, actor: Actor) {
      setListingStatus(this.db, ids, status, actor)
      this.persist()
    },
    saveCategory(input: NamedDraft, actor: Actor) {
      const result = saveCategory(this.db, input, actor)

      this.persist()

      return result
    },
    setCategoryActive(ids: string[], active: boolean, actor: Actor) {
      setCategoryActive(this.db, ids, active, actor)
      this.persist()
    },
    saveBrand(input: NamedDraft, actor: Actor) {
      const result = saveBrand(this.db, input, actor)

      this.persist()

      return result
    },
    setBrandActive(ids: string[], active: boolean, actor: Actor) {
      setBrandActive(this.db, ids, active, actor)
      this.persist()
    },
    saveMapping(input: MappingDraft, actor: Actor) {
      const result = saveMapping(this.db, input, actor)

      this.persist()

      return result
    },
    confirmMappings(ids: string[], actor: Actor) {
      confirmMappings(this.db, ids, actor)
      this.persist()
    },
    saveBundle(input: BundleDraft, actor: Actor) {
      const result = saveBundle(this.db, input, actor)

      this.persist()

      return result
    },
    removeBundles(ids: string[], actor: Actor) {
      removeBundles(this.db, ids, actor)
      this.persist()
    },
    disposeReturn(id: string, disposition: 'restock' | 'scrap', actor: Actor) {
      const result = disposeReturn(this.db, id, disposition, actor)

      this.persist()

      return result
    },
    registerReturn(orderId: string, disposition: 'restock' | 'scrap', actor: Actor) {
      const result = registerReturn(this.db, orderId, disposition, actor)

      this.persist()

      return result
    },
    createPurchase(input: PurchaseDraft, actor: Actor) {
      const result = createPurchaseOrder(this.db, input, actor)

      this.persist()

      return result
    },
    cancelPurchase(id: string, actor: Actor) {
      const result = cancelPurchaseOrder(this.db, id, actor)

      this.persist()

      return result
    },
    saveSupplier(input: SupplierDraft, actor: Actor) {
      const result = saveSupplier(this.db, input, actor)

      this.persist()

      return result
    },
    setSupplierStatus(ids: string[], status: 'active' | 'paused', actor: Actor) {
      setSupplierStatus(this.db, ids, status, actor)
      this.persist()
    },
    createPurchaseReturn(input: PurchaseReturnDraft, actor: Actor) {
      const result = createPurchaseReturn(this.db, input, actor)

      this.persist()

      return result
    },
    confirmPurchaseReturn(id: string, actor: Actor) {
      const result = confirmPurchaseReturn(this.db, id, actor)

      this.persist()

      return result
    },
    generateStatement(supplierId: string, period: string, actor: Actor) {
      const result = generateStatement(this.db, supplierId, period, actor)

      this.persist()

      return result
    },
    submitStatement(id: string, actor: Actor) {
      const result = submitStatement(this.db, id, actor)

      this.persist()

      return result
    },
    createShipment(input: ShipmentDraft, actor: Actor) {
      const result = createShipment(this.db, input, actor)

      this.persist()

      return result
    },
    saveShipmentFee(input: ShipmentFeeDraft, actor: Actor) {
      const result = saveShipmentFee(this.db, input, actor)

      this.persist()

      return result
    },
    saveCarrier(input: CarrierDraft, actor: Actor) {
      const result = saveCarrier(this.db, input, actor)

      this.persist()

      return result
    },
    setCarrierActive(ids: string[], active: boolean, actor: Actor) {
      setCarrierActive(this.db, ids, active, actor)
      this.persist()
    },
    saveRateCard(input: RateDraft, actor: Actor) {
      const result = saveRateCard(this.db, input, actor)

      this.persist()

      return result
    },
    submitFreightCheck(id: string, actor: Actor) {
      const result = submitFreightCheck(this.db, id, actor)

      this.persist()

      return result
    },
    saveWarehouse(input: WarehouseDraft, actor: Actor) {
      const result = saveWarehouse(this.db, input, actor)

      this.persist()

      return result
    },
    setWarehouseActive(ids: string[], active: boolean, actor: Actor) {
      setWarehouseActive(this.db, ids, active, actor)
      this.persist()
    },
    createStockDoc(input: StockDocDraft, actor: Actor) {
      const result = createStockDoc(this.db, input, actor)

      this.persist()

      return result
    },
    postDraftDoc(id: string, actor: Actor) {
      const result = postDraftStockDoc(this.db, id, actor)

      this.persist()

      return result
    },
    postTransfer(id: string, actor: Actor) {
      const result = postTransfer(this.db, id, actor)

      this.persist()

      return result
    },
    postCount(id: string, actuals: CountActual[], actor: Actor) {
      const result = postStockCount(this.db, id, actuals, actor)

      this.persist()

      return result
    },
  },
})
