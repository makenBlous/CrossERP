/* eslint-disable max-statements-per-line */
import type { Actor, MockDatabase, VoucherEntity } from '@/types/entities'
import type { CurrencyCode } from '@/types/domain'
import { submitSuggestion } from '@/mocks/services/approvals'
import { writeAudit } from '@/mocks/services/audit'
import { nextId } from '@/mocks/services/ids'
import { type Minor, minorFromDecimal, toDisplay } from '@/utils/money'

export interface ImportBatchRow { id: string; fileName: string; connector: string; status: string; rows: number; errors: number; importedAt: string; failure?: string }
export interface FeeMapRow { id: string; platform: string; description: string; category: string; status: 'confirmed' | 'unmapped'; suggestion: string }
export interface ColumnMapRow { id: string; connector: string; name: string; fields: number; status: string; updatedAt: string }
export interface ExportRow { id: string; fileName: string; approvalId: string; target: string; sha256: string; createdAt: string; status: string }
export interface ClearingRow { id: string; payout: string; ar: string; currency: string; payoutAmount: number; arAmount: number; difference: number; status: string }
export interface AdImportRow { id: string; fileName: string; platform: string; rows: number; spend: number; status: string; importedAt: string }
export interface AllocationRow { id: string; campaign: string; sku: string; ratio: number; spend: number; source: string }

const imports: ImportBatchRow[] = [
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

const feeMaps: FeeMapRow[] = [
  { id: 'fee-1', platform: 'Amazon', description: 'Commission', category: '平台佣金', status: 'confirmed', suggestion: '平台佣金' },
  { id: 'fee-2', platform: 'Amazon', description: 'FBA fulfillment fee', category: 'FBA 配送费', status: 'confirmed', suggestion: 'FBA 配送费' },
  { id: 'fee-3', platform: 'Shopify', description: 'Processing fee', category: '支付处理费', status: 'confirmed', suggestion: '支付处理费' },
  { id: 'fee-4', platform: 'Amazon', description: 'Promo rebate adjustment', category: '—', status: 'unmapped', suggestion: '促销折扣' },
]

const columnMaps: ColumnMapRow[] = [
  { id: 'map-lx-order', connector: 'lingxing', name: '领星订单导出', fields: 14, status: '已确认', updatedAt: '2026-10-31' },
  { id: 'map-lx-cost', connector: 'lingxing', name: '领星成本导出', fields: 8, status: '已确认', updatedAt: '2026-10-31' },
  { id: 'map-sf-order', connector: 'sellfox', name: '赛狐订单导出', fields: 12, status: '草稿', updatedAt: '2026-10-28' },
]

const adImports: AdImportRow[] = [
  { id: 'adimp-1', fileName: 'amazon-ads-2026-10.csv', platform: 'Amazon Ads', rows: 1240, spend: 3680.42, status: 'success', importedAt: '2026-11-01 10:12' },
  { id: 'adimp-2', fileName: 'shopify-meta-2026-10.csv', platform: 'Meta', rows: 382, spend: 924.18, status: 'success', importedAt: '2026-11-01 10:20' },
]

const exports: ExportRow[] = []

const allocations: AllocationRow[] = []

export function listImports() { return imports }
export function importDetail(id: string) { return imports.find(row => row.id === id) ?? imports[0] }
export function sourceRow(table: string, id: string) {
  return { id, table, sourceFile: 'amazon-us-2026-10.txt', rowNo: 42, payload: { settlement_id: 'STL-US-2026-10', transaction_type: 'Order', amount: '128.40', currency: 'USD', sku: 'TENT-2P' } }
}
export function settlements(db: MockDatabase) {
  return db.settlements.map(row => ({ ...row, storeName: db.stores.find(store => store.id === row.storeId)?.name ?? row.storeId, totalDisplay: toDisplay(row.total, row.currency), matched: db.reconRuns.find(run => run.storeId === row.storeId)?.matched ?? 0 }))
}
export function settlementDetail(db: MockDatabase, id: string) {
  const row = db.settlements.find(item => item.id === id) ?? db.settlements[0]
  if (!row)
    return null
  const storeName = db.stores.find(store => store.id === row.storeId)?.name ?? row.storeId

  return {
    ...row,
    storeName,
    totalDisplay: toDisplay(row.total, row.currency),
    lines: [
      { id: `${row.id}-1`, type: 'Order', description: 'Principal', amount: toDisplay(Math.round(row.total * 0.86), row.currency) },
      { id: `${row.id}-2`, type: 'Fee', description: 'Commission', amount: toDisplay(-Math.round(row.total * 0.09), row.currency) },
      { id: `${row.id}-3`, type: 'Fee', description: 'FBA fulfillment fee', amount: toDisplay(-Math.round(row.total * 0.05), row.currency) },
    ],
  }
}
export function reconDetail(db: MockDatabase, id: string) {
  const run = db.reconRuns.find(item => item.id === id) ?? db.reconRuns[0]
  if (!run)
    return null

  return {
    ...run,
    storeName: db.stores.find(store => store.id === run.storeId)?.name ?? run.storeId,
    groups: [
      { id: `${id}-g1`, status: 'matched', reference: 'ORDER-110-1000001-2000001', amount: '128.40 USD', reason: '订单号 + 金额一致' },
      { id: `${id}-g2`, status: 'unmatched', reference: 'ORDER-110-1000012-2000012', amount: '12.40 USD', reason: 'AMOUNT_MISMATCH' },
      { id: `${id}-g3`, status: 'unmatched', reference: 'SETTLEMENT-ADJ-004', amount: '5.00 USD', reason: 'UNKNOWN_FEE_TYPE' },
    ],
  }
}
export function issueDetail(db: MockDatabase, id: string) {
  const issue = db.issues.find(item => item.id === id) ?? db.issues[0]
  if (!issue)
    return null

  return { ...issue, storeName: db.stores.find(store => store.id === issue.storeId)?.name ?? issue.storeId, timeline: db.audit.filter(event => event.refId === issue.id).map(event => ({ at: event.at, title: event.action, detail: event.summary, actor: event.actor })) }
}
export function voucherDetail(db: MockDatabase, id: string) {
  const voucher = db.vouchers.find(item => item.id === id) ?? db.vouchers[0]
  if (!voucher)
    return null

  return { ...voucher, lines: [{ seq: 1, account: '主营业务成本', summary: voucher.summary, debit: toDisplay(voucher.debit, 'CNY'), credit: 0 }, { seq: 2, account: '平台结算清算', summary: voucher.summary, debit: 0, credit: toDisplay(voucher.credit, 'CNY') }], timeline: db.audit.filter(event => event.refId === voucher.id).map(event => ({ at: event.at, title: event.action, detail: event.summary, actor: event.actor })) }
}
export function accounts(db: MockDatabase) { return db.accounts.map(item => ({ ...item, review: item.code !== '6001' })) }
export function fxRates(db: MockDatabase) { return db.fxRates }
export function feeMapRows() { return feeMaps }
export function columnMapRows() { return columnMaps }
export function arRows(db: MockDatabase) { return db.arInvoices.map(row => ({ ...row, storeName: db.stores.find(store => store.id === row.storeId)?.name ?? row.storeId, amountDisplay: toDisplay(row.amount, row.currency), bucket: '0–30 天' })) }
export function apRows(db: MockDatabase) { return db.apInvoices.map(row => ({ ...row, supplier: db.suppliers.find(supplier => supplier.id === row.supplierId)?.name ?? row.supplierId, amountDisplay: toDisplay(row.amount, row.currency), bucket: '0–30 天' })) }
export function clearingRows(db: MockDatabase): ClearingRow[] { return db.settlements.slice(0, 6).map((row, index) => ({ id: `clr-${index + 1}`, payout: row.externalId, ar: `AR-${row.storeId}`, currency: row.currency, payoutAmount: toDisplay(row.total, row.currency), arAmount: toDisplay(row.total, row.currency), difference: 0, status: index === 0 ? '待核销' : '候选' })) }
export function exportRows(db: MockDatabase) {
  const generated = db.approvals.filter(item => item.status === 'approved').map(item => ({ id: `exp-${item.id}`, fileName: `${item.targetId}.xlsx`, approvalId: item.id, target: 'generic_xlsx', sha256: `sha256:${item.id.slice(-8)}`, createdAt: item.submittedAt, status: '可下载' }))

  return [...exports, ...generated]
}
export function cashRows(db: MockDatabase) { return db.settlements.slice(0, 10).map(row => ({ id: row.id, date: row.periodEnd, account: row.externalId, direction: '收入', amount: toDisplay(row.total, row.currency), currency: row.currency, source: row.platform })) }
export function adsCampaigns(db: MockDatabase) { return db.adsCampaigns.map(row => ({ ...row, storeName: db.stores.find(store => store.id === row.storeId)?.name ?? row.storeId, spendDisplay: toDisplay(row.spend, row.currency) })) }
export function adsImportRows() { return adImports }
export function recordAdImport(db: MockDatabase, fileName: string, actor: Actor) {
  const row: AdImportRow = { id: `adimp-${adImports.length + 1}`, fileName, platform: 'Amazon Ads', rows: 128, spend: 418.36, status: 'success', importedAt: actor.at.slice(0, 16).replace('T', ' ') }

  adImports.unshift(row)
  writeAudit(db, actor, 'import_ads', 'ads_import', row.id, `导入广告花费文件 ${fileName}，解析 ${row.rows} 行。`)

  return row
}
export function adsPerformance(db: MockDatabase) { return adsCampaigns(db).map(row => ({ ...row, sales: row.spendDisplay * 4.6, roas: 4.6 })) }
export function allocationRows(db: MockDatabase) { return allocations.length ? allocations : db.skus.slice(0, 5).map((sku, index) => ({ id: `alloc-${index + 1}`, campaign: db.adsCampaigns[0]?.name ?? '秋季活动', sku: sku.internalSku, ratio: index === 0 ? 40 : 15, spend: 0, source: '演示计提 5%' })) }

export function confirmFeeMap(db: MockDatabase, id: string, category: string, actor: Actor) {
  const row = feeMaps.find(item => item.id === id)
  if (!row)
    return
  row.category = category; row.status = 'confirmed'; writeAudit(db, actor, 'confirm_fee_map', 'fee_map', id, `人工确认费用映射为 ${category}。AI 仅提供建议。`)
  db.issues.filter(issue => issue.code === 'UNKNOWN_FEE_TYPE' && issue.status === 'open').slice(0, 1).forEach(issue => { issue.status = 'explained' })
}
export function handleIssue(db: MockDatabase, id: string, action: 'explained' | 'ignored', note: string, actor: Actor) {
  const row = db.issues.find(item => item.id === id)
  if (!row)
    return
  row.status = action; row.summary = note || row.summary; writeAudit(db, actor, action, 'issue', id, note || `异常标记为 ${action}`)
}
export function createVoucherFromIssue(db: MockDatabase, issueId: string, actor: Actor) {
  const issue = db.issues.find(item => item.id === issueId)
  if (!issue)
    return null
  const voucher: VoucherEntity = { id: nextId(db, 'vch'), no: `记-2026-11-${String(db.vouchers.length + 1).padStart(3, '0')}`, period: '2026-11', status: 'pending', debit: issue.amount, credit: issue.amount, currency: 'CNY', summary: `异常 ${issue.id} 处理凭证`, submitter: actor.name }

  db.vouchers.push(voucher)
  submitSuggestion(db, { title: voucher.summary, summary: '借贷由服务层按异常已存金额生成，页面不计算。', amount: String(toDisplay(issue.amount, 'CNY')), currency: 'CNY', storeId: issue.storeId, targetType: 'voucher', targetId: voucher.id }, actor)

  return voucher
}
export function createVoucherFromProfit(db: MockDatabase, actor: Actor) {
  const total = db.profitSnapshots.filter(row => row.period === '2026-10').reduce((sum, row) => sum + row.profit, 0)
  const amount: Minor = total || minorFromDecimal('100.0000')
  const voucher: VoucherEntity = { id: nextId(db, 'vch'), no: `记-2026-10-${String(db.vouchers.length + 1).padStart(3, '0')}`, period: '2026-10', status: 'pending', debit: amount, credit: amount, currency: 'CNY', summary: '10 月利润结转草稿', submitter: actor.name }

  db.vouchers.push(voucher)
  submitSuggestion(db, { title: voucher.summary, summary: '利润快照已由确定性服务计算，提交审批后才能过账。', amount: String(toDisplay(amount, 'CNY')), currency: 'CNY', storeId: null, targetType: 'voucher', targetId: voucher.id }, actor)

  return voucher
}
export function saveAllocation(db: MockDatabase, sku: string, ratio: number, actor: Actor) {
  const campaign = db.adsCampaigns[0]
  if (!campaign)
    return
  const row = { id: `alloc-${allocations.length + 1}`, campaign: campaign.name, sku, ratio, spend: toDisplay(Math.round(campaign.spend * ratio / 100), campaign.currency), source: '广告分摊' }

  allocations.push(row)

  const snapshot = db.profitSnapshots.find(item => item.internalSku === sku && item.period === '2026-10')
  if (snapshot) { snapshot.ads = Math.round(campaign.spend * ratio / 100); snapshot.profit -= snapshot.ads }
  writeAudit(db, actor, 'save_allocation', 'ads_allocation', row.id, `保存 ${sku} 广告分摊规则 ${ratio}%。`)

  return row
}

export function submitClearing(db: MockDatabase, actor: Actor) {
  const row = clearingRows(db)[0]
  if (!row)
    return null

  return submitSuggestion(db, { title: `核销 ${row.payout}`, summary: '两侧金额由服务层校验相等后提交审批。', amount: String(row.payoutAmount), currency: row.currency as CurrencyCode, storeId: null, targetType: 'clearing', targetId: row.id }, actor)
}
