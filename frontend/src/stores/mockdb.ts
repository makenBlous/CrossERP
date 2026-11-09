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
import { arriveShipment, departShipment } from '@/mocks/services/logistics'
import { disposeReturn, registerReturn, shipSalesOrder } from '@/mocks/services/orders'
import { approvePurchaseOrder, receivePurchaseOrder, rejectPurchaseOrder, submitPurchaseOrder } from '@/mocks/services/procurement'
import { MOCK_DB_VERSION, buildSeed } from '@/mocks/seed/build'
import type { Actor, MockDatabase } from '@/types/entities'
import { addTicket, convertLead, createToken, resetRoleOverride, revokeToken, saveRoleOverride, updateLeadStage, updateTicketStatus } from '@/mocks/services/crm-admin'

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

    if (isDatabase(parsed)) {
      const fresh = buildSeed()
      if (!Array.isArray(parsed.crmLeads))
        parsed.crmLeads = fresh.crmLeads
      if (!Array.isArray(parsed.crmActivities))
        parsed.crmActivities = fresh.crmActivities
      if (!Array.isArray(parsed.crmReviews))
        parsed.crmReviews = fresh.crmReviews
      if (!Array.isArray(parsed.crmTicketMessages))
        parsed.crmTicketMessages = fresh.crmTicketMessages
      if (!Array.isArray(parsed.roleOverrides))
        parsed.roleOverrides = fresh.roleOverrides
      if (!Array.isArray(parsed.adminIntegrations))
        parsed.adminIntegrations = fresh.adminIntegrations
      if (!Array.isArray(parsed.adminModules))
        parsed.adminModules = fresh.adminModules
      if (!Array.isArray(parsed.adminDicts))
        parsed.adminDicts = fresh.adminDicts
      if (!Array.isArray(parsed.adminNotifications))
        parsed.adminNotifications = fresh.adminNotifications
      if (!Array.isArray(parsed.adminSettings))
        parsed.adminSettings = fresh.adminSettings
      if (!Array.isArray(parsed.accountTokens))
        parsed.accountTokens = fresh.accountTokens
      if (!Array.isArray(parsed.accountSessions))
        parsed.accountSessions = fresh.accountSessions

      return parsed
    }
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
    decide(id: string, status: 'approved' | 'rejected', actor: Actor) {
      const result = decideApproval(this.db, id, status, actor)

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
    updateLeadStage(id: string, stage: Parameters<typeof updateLeadStage>[2], actor: Actor) {
      const result = updateLeadStage(this.db, id, stage, actor)

      this.persist()

      return result
    },
    convertLead(id: string, actor: Actor) {
      const result = convertLead(this.db, id, actor)

      this.persist()

      return result
    },
    addTicket(input: { accountId: string; orderNo: string | null; subject: string }, actor: Actor) {
      const result = addTicket(this.db, input, actor)

      this.persist()

      return result
    },
    updateTicketStatus(id: string, status: string, actor: Actor) {
      const result = updateTicketStatus(this.db, id, status, actor)

      this.persist()

      return result
    },
    saveRoleOverride(role: Actor['role'], hiddenGroups: string[], hiddenPageIds: string[], actor: Actor) {
      saveRoleOverride(this.db, role, hiddenGroups, hiddenPageIds, actor)
      this.persist()
    },
    resetRoleOverride(role: Actor['role'], actor: Actor) {
      resetRoleOverride(this.db, role, actor)
      this.persist()
    },
    createToken(name: string, actor: Actor) {
      const result = createToken(this.db, name, actor)

      this.persist()

      return result
    },
    revokeToken(id: string, actor: Actor) {
      const result = revokeToken(this.db, id, actor)

      this.persist()

      return result
    },
  },
})
