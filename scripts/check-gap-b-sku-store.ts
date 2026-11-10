import { strict as assert } from 'node:assert'

import { projectProfitSku } from '../frontend/src/mocks/project'
import { buildSeed } from '../frontend/src/mocks/seed/build'

const internalSku = 'NW-TENT-2P-OLV'
const period = '2026-06'
const db = buildSeed()

db.orders = [
  {
    id: 'ord-us-shipped',
    storeId: 'amz-us',
    orderNo: 'US-001',
    orderedAt: '2026-06-01T08:00:00Z',
    buyerRef: 'buyer-us',
    status: 'shipped',
    currency: 'USD',
    fulfillment: 'FBA',
    warehouseId: 'wh-fba-us',
    carrierName: 'Amazon Logistics',
    trackingNo: 'TRK-US-001',
    shippedAt: '2026-06-03T08:00:00Z',
    refund: 0,
  },
  {
    id: 'ord-us-paid',
    storeId: 'amz-us',
    orderNo: 'US-PAID',
    orderedAt: '2026-06-02T08:00:00Z',
    buyerRef: 'buyer-us-paid',
    status: 'paid',
    currency: 'USD',
    fulfillment: 'FBA',
    warehouseId: 'wh-fba-us',
    carrierName: 'Amazon Logistics',
    trackingNo: '',
    shippedAt: null,
    refund: 0,
  },
  {
    id: 'ord-jp-shipped',
    storeId: 'amz-jp',
    orderNo: 'ord-01233',
    orderedAt: '2026-06-03T08:00:00Z',
    buyerRef: 'buyer-jp',
    status: 'shipped',
    currency: 'JPY',
    fulfillment: 'FBA',
    warehouseId: 'wh-fba-jp',
    carrierName: 'Amazon Logistics',
    trackingNo: 'TRK-JP-001',
    shippedAt: '2026-06-05T08:00:00Z',
    refund: 0,
  },
]

db.orderLines = [
  { id: 'line-us-shipped', orderId: 'ord-us-shipped', internalSku, title: '双人帐篷', qty: 5, unitPrice: 624960, currency: 'USD' },
  { id: 'line-us-paid', orderId: 'ord-us-paid', internalSku, title: '双人帐篷', qty: 1, unitPrice: 624960, currency: 'USD' },
  { id: 'line-jp-shipped', orderId: 'ord-jp-shipped', internalSku, title: '双人帐篷', qty: 1, unitPrice: 186555224, currency: 'JPY' },
]

db.profitSnapshots = [
  {
    id: 'snapshot-us', period, internalSku, storeId: 'amz-us', currency: 'USD',
    revenue: 3124800, fees: 0, refunds: 0, cogs: 0, freight: 0, ads: 0, profit: 3124800, calcVersion: 'check',
  },
  {
    id: 'snapshot-jp', period, internalSku, storeId: 'amz-jp', currency: 'JPY',
    revenue: 186555224, fees: 0, refunds: 0, cogs: 0, freight: 0, ads: 0, profit: 186555224, calcVersion: 'check',
  },
]

const result = projectProfitSku(db, internalSku, period)
assert.ok(result, '应返回 SKU 利润详情')
assert.equal(result.row.storeId, 'amz-us', '没有店铺参数时默认第一个有数据店铺')
assert.deepEqual(result.rows.map(row => row.storeId), ['amz-us', 'amz-jp'])
assert.deepEqual(result.rows.map(row => row.currency), ['USD', 'JPY'])
assert.equal(result.rows.find(row => row.storeId === 'amz-us')?.revenue, 3124800)
assert.equal(result.rows.find(row => row.storeId === 'amz-jp')?.revenue, 186555224)
assert.deepEqual(Object.keys(result).filter(key => /total|sum/i.test(key)), [], '不同币种不应直接相加')

for (const row of result.rows) {
  assert.equal(db.stores.find(store => store.id === row.storeId)?.currency, row.currency)
  const selected = projectProfitSku(db, internalSku, period, row.storeId)

  assert.ok(selected, `${row.storeId} 应可切换查看`)
  assert.equal(selected.row.storeId, row.storeId)
  assert.ok(selected.sourceOrders.length > 0)
  assert.ok(selected.sourceOrders.every(order => order.storeId === row.storeId))
  assert.ok(selected.sourceOrders.every(order => order.currency === row.currency))
  assert.ok(selected.sourceOrders.every(order => order.storeName === row.storeName))
  assert.ok(selected.sourceOrders.every(order => order.id !== 'ord-us-paid'))
}

const jp = projectProfitSku(db, internalSku, period, 'amz-jp')
assert.ok(jp)
assert.equal(jp.row.currency, 'JPY')
assert.deepEqual(jp.sourceOrders.map(order => order.id), ['ord-jp-shipped'])

const invalidStore = projectProfitSku(db, internalSku, period, 'missing-store')
assert.ok(invalidStore)
assert.equal(invalidStore.row.storeId, 'amz-us', '无数据店铺参数时回退第一个有数据店铺')

console.log('gap-b SKU 店铺/币种/来源订单断言通过')
