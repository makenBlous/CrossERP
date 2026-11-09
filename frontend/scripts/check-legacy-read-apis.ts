import { strict as assert } from 'node:assert'
import { readFileSync } from 'node:fs'
import { createPinia, setActivePinia } from 'pinia'
import { fetchAccounts, fetchAp, fetchApAging, fetchAr, fetchArAging, fetchCash, fetchClearing, fetchColumnMaps, fetchExports, fetchFeeMap, fetchFxRates, fetchImports, fetchSettlements, fetchVouchers } from '@/api/finance'
import { fetchAlerts, fetchBalances, fetchMovements, fetchOnHand, fetchStockDocs, fetchWarehouses } from '@/api/inventory'
import { fetchChannels, fetchExceptions, fetchFulfillment, fetchOrders, fetchReturns } from '@/api/orders'
import { fetchPurchaseOrders, fetchPurchaseReturns, fetchReceipts, fetchStatements, fetchSuppliers, fetchSupplyLookups } from '@/api/procurement'
import { useSessionStore } from '@/stores/session'
import type { Role } from '@/types/domain'
import { can } from '@/utils/permission'
import { canRoleOpen, pageCatalog } from '@/config/pages'

interface ReadApi {
  name: string
  pagePath: string
  call: () => Promise<unknown>
}

const legacyRoles: Role[] = ['admin', 'operator', 'finance', 'viewer', 'auditor']
const baseline = JSON.parse(readFileSync(`${process.env.TEMP}/cx-pw/b0_base_pages.json`, 'utf8').replace(/^\uFEFF/, '')) as Array<{ path: string; roles: Role[] }>
const baselineByPath = new Map(baseline.map(item => [item.path, item]))

// 旧兼容 API 的 read 动作名是 view；这就是旧 can(role, 'read') 的等价检查。
function legacyCanRead(role: Role) {
  return can(role, 'view')
}

const readApis: ReadApi[] = [
  { name: 'payments/ar', pagePath: '/finance/ar', call: fetchAr },
  { name: 'payments/ar-aging', pagePath: '/finance/ar', call: fetchArAging },
  { name: 'payments/ap', pagePath: '/finance/ap', call: fetchAp },
  { name: 'payments/ap-aging', pagePath: '/finance/ap', call: fetchApAging },
  { name: 'clearing', pagePath: '/finance/clearing', call: fetchClearing },
  { name: 'cash', pagePath: '/finance/cash', call: fetchCash },
  { name: 'vouchers', pagePath: '/finance/vouchers', call: fetchVouchers },
  { name: 'settlements', pagePath: '/finance/settlements', call: fetchSettlements },
  { name: 'finance/accounts', pagePath: '/finance/accounts', call: fetchAccounts },
  { name: 'finance/fx-rates', pagePath: '/finance/fx-rates', call: fetchFxRates },
  { name: 'finance/fee-map', pagePath: '/finance/fee-map', call: fetchFeeMap },
  { name: 'finance/column-maps', pagePath: '/finance/column-maps', call: fetchColumnMaps },
  { name: 'finance/imports', pagePath: '/finance/imports', call: fetchImports },
  { name: 'finance/exports', pagePath: '/finance/exports', call: fetchExports },
  { name: 'orders', pagePath: '/orders', call: fetchOrders },
  { name: 'orders/returns', pagePath: '/orders/returns', call: fetchReturns },
  { name: 'orders/exceptions', pagePath: '/orders/exceptions', call: fetchExceptions },
  { name: 'orders/channels', pagePath: '/orders/channels', call: fetchChannels },
  { name: 'orders/fulfillment', pagePath: '/orders/fulfillment', call: fetchFulfillment },
  { name: 'inventory/warehouses', pagePath: '/inventory/warehouses', call: fetchWarehouses },
  { name: 'inventory/on-hand', pagePath: '/inventory/on-hand', call: fetchOnHand },
  { name: 'inventory/fba', pagePath: '/inventory/fba', call: () => fetchBalances('fba') },
  { name: 'inventory/overseas', pagePath: '/inventory/overseas', call: () => fetchBalances('overseas') },
  { name: 'inventory/domestic', pagePath: '/inventory/domestic', call: () => fetchBalances('domestic') },
  { name: 'inventory/movements', pagePath: '/inventory/movements', call: fetchMovements },
  { name: 'inventory/inbound', pagePath: '/inventory/inbound', call: () => fetchStockDocs('inbound') },
  { name: 'inventory/outbound', pagePath: '/inventory/outbound', call: () => fetchStockDocs('outbound') },
  { name: 'inventory/transfers', pagePath: '/inventory/transfers', call: () => fetchStockDocs('transfer') },
  { name: 'inventory/counts', pagePath: '/inventory/counts', call: () => fetchStockDocs('count') },
  { name: 'inventory/alerts', pagePath: '/inventory/alerts', call: fetchAlerts },
  { name: 'procurement/lookups', pagePath: '/procurement/orders', call: fetchSupplyLookups },
  { name: 'procurement/suppliers', pagePath: '/procurement/suppliers', call: fetchSuppliers },
  { name: 'procurement/orders', pagePath: '/procurement/orders', call: fetchPurchaseOrders },
  { name: 'procurement/receipts', pagePath: '/procurement/receipts', call: fetchReceipts },
  { name: 'procurement/returns', pagePath: '/procurement/returns', call: fetchPurchaseReturns },
  { name: 'procurement/statements', pagePath: '/procurement/statements', call: fetchStatements },
]

setActivePinia(createPinia())

const session = useSessionStore()
let fail = 0
let calls = 0

for (const role of legacyRoles) {
  session.setRole(role)
  for (const api of readApis) {
    const page = pageCatalog.find(item => item.path === api.pagePath)
    const expectedPage = baselineByPath.get(api.pagePath)?.roles.includes(role) ?? false
    const oldRead = legacyCanRead(role)

    assert(page, `缺少旧页面定义 ${api.pagePath}`)
    assert.equal(canRoleOpen(role, page), expectedPage, `${role} 页面权限与基线不一致：${api.pagePath}`)

    if (!expectedPage || !oldRead)
      continue

    calls++
    try {
      await api.call()
      console.log(`PASS ${role} ${api.name}（旧 read=${oldRead}）`)
    }
    catch (error) {
      fail++
      console.log(`FAIL ${role} ${api.name}（旧 read=${oldRead}）：${error instanceof Error ? error.message : String(error)}`)
    }
  }
}

console.log(`== FAIL ${fail}`)
console.log(`legacy read APIs checked: ${calls}`)
process.exit(fail ? 1 : 0)
