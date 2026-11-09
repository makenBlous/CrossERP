import { defineStore } from 'pinia'
import { type SuggestionInput, decideApproval, submitSuggestion } from '@/mocks/services/approvals'
import { arriveShipment, departShipment } from '@/mocks/services/logistics'
import { shipSalesOrder } from '@/mocks/services/orders'
import { approvePurchaseOrder, receivePurchaseOrder, rejectPurchaseOrder, submitPurchaseOrder } from '@/mocks/services/procurement'
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
    decide(id: string, status: 'approved' | 'rejected', actor: Actor) {
      const result = decideApproval(this.db, id, status, actor)

      this.persist()

      return result
    },
  },
})
