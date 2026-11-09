import type { Finance2Data, MockDatabase } from '@/types/entities'

const IMPORTS: Finance2Data['imports'] = [
  { id: 'imp-001', fileName: 'amazon-us-2026-10.txt', connector: 'Amazon Settlement V2', status: 'success', rows: 428, errors: 0, importedAt: '2026-11-02 09:14' },
  { id: 'imp-002', fileName: 'amazon-uk-2026-10.txt', connector: 'Amazon Settlement V2', status: 'success', rows: 216, errors: 2, importedAt: '2026-11-02 09:18', failure: '2 行未知费用类型' },
  { id: 'imp-003', fileName: 'shopify-2026-10.csv', connector: 'Shopify Payments', status: 'success', rows: 96, errors: 0, importedAt: '2026-11-01 16:22' },
  { id: 'imp-004', fileName: 'tiktok-2026-10.csv', connector: 'Generic mapped', status: 'failed', rows: 0, errors: 1, importedAt: '2026-11-01 12:03', failure: '列映射缺少 payout_id' },
  { id: 'imp-005', fileName: 'amazon-de-2026-10.txt', connector: 'Amazon Settlement V2', status: 'success', rows: 302, errors: 1, importedAt: '2026-10-31 19:45', failure: '1 行金额格式待核实' },
  { id: 'imp-006', fileName: 'lingxing-cost-oct.xlsx', connector: '领星映射', status: 'success', rows: 24, errors: 0, importedAt: '2026-10-31 10:20' },
  { id: 'imp-007', fileName: 'sellfox-fx-oct.xlsx', connector: '赛狐映射', status: 'success', rows: 8, errors: 0, importedAt: '2026-10-30 15:07' },
  { id: 'imp-008', fileName: 'amazon-jp-2026-10.txt', connector: 'Amazon Settlement V2', status: 'success', rows: 188, errors: 0, importedAt: '2026-10-29 08:42' },
  { id: 'imp-009', fileName: 'amazon-us-2026-09.txt', connector: 'Amazon Settlement V2', status: 'success', rows: 391, errors: 0, importedAt: '2026-10-03 11:22' },
  { id: 'imp-010', fileName: 'shopify-2026-09.csv', connector: 'Shopify Payments', status: 'success', rows: 88, errors: 0, importedAt: '2026-10-02 13:01' },
  { id: 'imp-011', fileName: 'amazon-us-retry.txt', connector: 'Amazon Settlement V2', status: 'failed', rows: 0, errors: 1, importedAt: '2026-09-28 18:03', failure: '文件编码无法识别' },
  { id: 'imp-012', fileName: 'lingxing-orders-oct.xlsx', connector: '领星映射', status: 'success', rows: 114, errors: 0, importedAt: '2026-10-28 09:30' },
]

export function seedFinance(db: MockDatabase) {
  db.finance2 = {
    imports: IMPORTS.map(row => ({ ...row })),
    feeMaps: [
      { id: 'fee-1', platform: 'Amazon', description: 'Commission', category: '平台佣金', status: 'confirmed', suggestion: '平台佣金' },
      { id: 'fee-2', platform: 'Amazon', description: 'FBA fulfillment fee', category: 'FBA 配送费', status: 'confirmed', suggestion: 'FBA 配送费' },
      { id: 'fee-3', platform: 'Shopify', description: 'Processing fee', category: '支付处理费', status: 'confirmed', suggestion: '支付处理费' },
      { id: 'fee-4', platform: 'Amazon', description: 'Promo rebate adjustment', category: '—', status: 'unmapped', suggestion: '促销折扣' },
    ],
    columnMaps: [
      { id: 'map-lx-order', connector: 'lingxing', name: '领星订单导出', fields: 14, status: 'confirmed', updatedAt: '2026-10-31', mappings: [{ source: '订单号', field: 'order_no' }, { source: 'SKU', field: 'platform_sku' }, { source: '金额', field: 'amount' }] },
      { id: 'map-lx-cost', connector: 'lingxing', name: '领星成本导出', fields: 8, status: 'confirmed', updatedAt: '2026-10-31', mappings: [{ source: 'SKU', field: 'internal_sku' }, { source: '成本', field: 'unit_cost' }, { source: '生效日期', field: 'valid_from' }] },
      { id: 'map-sf-order', connector: 'sellfox', name: '赛狐订单导出', fields: 12, status: 'draft', updatedAt: '2026-10-28', mappings: [{ source: '订单编号', field: 'order_no' }, { source: '平台 SKU', field: 'platform_sku' }, { source: '销售额', field: 'amount' }] },
    ],
    exports: [],
    clearing: db.settlements.slice(0, 6).map((row, index) => {
      const ar = db.arInvoices.find(item => item.storeId === row.storeId)
      const arAmount = ar?.amount ?? row.total

      return {
        id: `clr-${index + 1}`,
        payout: row.externalId,
        ar: ar?.id ?? `AR-${row.storeId}`,
        currency: row.currency,
        payoutAmount: row.total,
        arAmount,
        difference: row.total - arAmount,
        status: index === 0 ? 'pending' : 'candidate',
      }
    }),
  }
}
