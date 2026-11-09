import type { CurrencyCode } from '@/types/domain'
import type { Actor, AdsAllocation, AdsImportBatch, Finance2Data, MockDatabase, VoucherEntity } from '@/types/entities'
import { submitSuggestion } from '@/mocks/services/approvals'
import { writeAudit } from '@/mocks/services/audit'
import { nextId } from '@/mocks/services/ids'
import { type Minor, addMinor, convertMinor, minorFromDecimal, minorToDecimal, toDisplay } from '@/utils/money'
import { requireActorPermission } from '@/utils/service-permissions'

export type ImportBatchRow = Finance2Data['imports'][number]
export type FeeMapRow = Finance2Data['feeMaps'][number]
export type ColumnMapRow = Finance2Data['columnMaps'][number]
export type ExportRow = Finance2Data['exports'][number]
export type ClearingRow = Finance2Data['clearing'][number]
export type AdImportRow = AdsImportBatch
export type AllocationRow = AdsAllocation

function financeData(db: MockDatabase): Finance2Data {
  if (!db.finance2)
    db.finance2 = { imports: [], feeMaps: [], columnMaps: [], exports: [], clearing: [] }

  return db.finance2
}

function adsData(db: MockDatabase) {
  if (!db.ads)
    db.ads = { imports: [], allocations: [] }

  return db.ads
}

export function listImports(db: MockDatabase) {
  return financeData(db).imports
}

export function importDetail(db: MockDatabase, id: string) {
  return financeData(db).imports.find(row => row.id === id) ?? null
}

export function recordImport(db: MockDatabase, fileName: string, actor: Actor) {
  requireActorPermission(actor, 'integration:import')

  const data = financeData(db)
  const row = { id: `imp-${String(data.imports.length + 1).padStart(3, '0')}`, fileName, connector: 'Auto-detect', status: 'success', rows: 64, errors: 0, importedAt: new Date(actor.at).toLocaleString('sv-SE').slice(0, 16) }

  data.imports.unshift(row)
  writeAudit(db, actor, 'import_file', 'import_batch', row.id, `导入文件 ${fileName}，解析 ${row.rows} 行。`)

  return row
}

export function sourceRow(table: string, id: string) {
  if (id !== 'row-42' && !id.endsWith('-row-1'))
    return null

  const settlementId = id.replace(/-row-1$/, '')

  return { id, table, sourceFile: 'amazon-us-2026-10.txt', rowNo: id === 'row-42' ? 42 : 1, payload: { settlement_id: settlementId === id ? 'STL-US-2026-10' : settlementId, transaction_type: 'Order', amount: '128.40', currency: 'USD', sku: 'TENT-2P' } }
}

export function settlements(db: MockDatabase) {
  return db.settlements.map(row => ({ ...row, storeName: db.stores.find(store => store.id === row.storeId)?.name ?? row.storeId, totalDisplay: toDisplay(row.total, row.currency), rawRowId: `${row.id}-row-1`, matched: db.reconRuns.find(run => run.storeId === row.storeId)?.matched ?? 0 }))
}

export function settlementDetail(db: MockDatabase, id: string) {
  const row = db.settlements.find(item => item.id === id)
  if (!row)
    return null

  return {
    ...row,
    storeName: db.stores.find(store => store.id === row.storeId)?.name ?? row.storeId,
    totalDisplay: toDisplay(row.total, row.currency),
    rawRowId: `${row.id}-row-1`,
    lines: [
      { id: `${row.id}-1`, type: 'Order', description: 'Principal', amount: Math.round(row.total * 86 / 100) },
      { id: `${row.id}-2`, type: 'Fee', description: 'Commission', amount: -Math.round(row.total * 9 / 100) },
      { id: `${row.id}-3`, type: 'Fee', description: 'FBA fulfillment fee', amount: -Math.round(row.total * 5 / 100) },
    ],
  }
}

export function reconDetail(db: MockDatabase, id: string) {
  const run = db.reconRuns.find(item => item.id === id)
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
  const issue = db.issues.find(item => item.id === id)
  if (!issue)
    return null

  return { ...issue, storeName: db.stores.find(store => store.id === issue.storeId)?.name ?? issue.storeId, timeline: db.audit.filter(event => event.refId === issue.id).map(event => ({ at: event.at, title: event.action, detail: event.summary, actor: event.actor })) }
}

export function voucherDetail(db: MockDatabase, id: string) {
  const voucher = db.vouchers.find(item => item.id === id)
  if (!voucher)
    return null
  const lines = [{ seq: 1, account: '主营业务成本', summary: voucher.summary, debit: voucher.debit, credit: 0 }, { seq: 2, account: '平台结算清算', summary: voucher.summary, debit: 0, credit: voucher.credit }]
  const debit = lines.reduce((sum, line) => sum + line.debit, 0)
  const credit = lines.reduce((sum, line) => sum + line.credit, 0)

  return { ...voucher, lines, debit, credit, balanced: debit === credit, difference: debit - credit, approvalId: db.approvals.filter(item => item.targetType === 'voucher' && item.targetId === voucher.id).at(-1)?.id, approvalIds: db.approvals.filter(item => item.targetType === 'voucher' && item.targetId === voucher.id).map(item => item.id), timeline: db.audit.filter(event => event.refId === voucher.id).map(event => ({ at: event.at, title: event.action, detail: event.summary, actor: event.actor })) }
}

export function accounts(db: MockDatabase) {
  return db.accounts.map(item => ({ ...item, group: item.direction === 'debit' ? (item.code.startsWith('1') ? '资产' : '费用') : (item.code.startsWith('2') ? '负债' : '收入'), review: item.code !== '6001' }))
}

export function fxRates(db: MockDatabase) {
  return db.fxRates
}

export function addFxRate(db: MockDatabase, input: { period: string; fromCcy: CurrencyCode; toCcy: CurrencyCode; rate: string }, actor: Actor) {
  requireActorPermission(actor, 'integration:write')

  const rate = minorFromDecimal(input.rate)
  if (rate <= 0)
    return null
  const row = { id: `fx-${db.fxRates.length + 1}`, period: input.period, fromCcy: input.fromCcy, toCcy: input.toCcy, rate: input.rate, source: '用户提供' }

  db.fxRates.push(row)
  writeAudit(db, actor, 'add_fx_rate', 'fx_rate', row.id, `新增 ${row.period} ${row.fromCcy}/${row.toCcy} 汇率。`)

  return row
}

export function feeMapRows(db: MockDatabase) {
  return financeData(db).feeMaps
}

export function columnMapRows(db: MockDatabase) {
  return financeData(db).columnMaps
}

export function columnMapDetail(db: MockDatabase, id: string) {
  return financeData(db).columnMaps.find(row => row.id === id) ?? null
}

export function saveColumnMap(db: MockDatabase, id: string, mappings: Array<{ source: string; field: string }>, actor: Actor) {
  requireActorPermission(actor, 'integration:write')

  const row = financeData(db).columnMaps.find(item => item.id === id)
  if (!row)
    return null
  row.mappings = mappings.map(item => ({ ...item }))
  row.fields = mappings.length
  row.status = 'confirmed'
  row.updatedAt = actor.at.slice(0, 10)
  writeAudit(db, actor, 'update_column_map', 'column_map', id, `保存列映射 ${row.name}，共 ${mappings.length} 个字段。`)

  return row
}

function agingBucket(dueAt: string) {
  const days = Math.max(0, Math.floor((Date.parse('2026-11-09') - Date.parse(`${dueAt}T00:00:00Z`)) / 86400000))

  return days <= 30 ? '0-30' : days <= 60 ? '31-60' : days <= 90 ? '61-90' : '90+'
}

export interface AgingSummary {
  key: string
  count: number
  amounts: Array<{ currency: CurrencyCode; amount: number }>
}

function agingSummary(rows: Array<{ amount: number; currency: CurrencyCode; dueAt: string }>): AgingSummary[] {
  const keys = ['0-30', '31-60', '61-90', '90+']

  return keys.map(key => {
    const grouped = new Map<CurrencyCode, number>()
    const matching = rows.filter(row => agingBucket(row.dueAt) === key)

    matching.forEach(row => grouped.set(row.currency, (grouped.get(row.currency) ?? 0) + row.amount))

    return { key, count: matching.length, amounts: [...grouped.entries()].map(([currency, amount]) => ({ currency, amount })) }
  })
}

export function arRows(db: MockDatabase) {
  return db.arInvoices.map(row => ({ ...row, storeName: db.stores.find(store => store.id === row.storeId)?.name ?? row.storeId, amountDisplay: toDisplay(row.amount, row.currency), bucket: agingBucket(row.dueAt) }))
}

export function apRows(db: MockDatabase) {
  return db.apInvoices.map(row => ({ ...row, supplier: db.suppliers.find(supplier => supplier.id === row.supplierId)?.name ?? row.supplierId, amountDisplay: toDisplay(row.amount, row.currency), bucket: agingBucket(row.dueAt) }))
}

export function arAging(db: MockDatabase) {
  return agingSummary(db.arInvoices)
}

export function apAging(db: MockDatabase) {
  return agingSummary(db.apInvoices)
}

export function clearingRows(db: MockDatabase) {
  const data = financeData(db)

  if (!data.clearing.length) {
    db.settlements.slice(0, 6).forEach((settlement, index) => {
      const ar = db.arInvoices.find(item => item.storeId === settlement.storeId && item.currency === settlement.currency)

      data.clearing.push({ id: `clr-${index + 1}`, payout: settlement.externalId, ar: ar?.id ?? `AR-${settlement.storeId}`, currency: settlement.currency, payoutAmount: settlement.total, arAmount: ar?.amount ?? settlement.total, difference: settlement.total - (ar?.amount ?? settlement.total), status: index === 0 ? 'pending' : 'candidate' })
    })
  }

  return data.clearing
}

export function exportRows(db: MockDatabase) {
  return financeData(db).exports
}

export function cashRows(db: MockDatabase) {
  return db.settlements.slice(0, 10).map(row => ({ id: row.id, date: row.periodEnd, account: row.externalId, direction: 'in', amount: row.total, currency: row.currency, source: row.platform, status: 'pending' }))
}

export function adsCampaigns(db: MockDatabase) {
  return db.adsCampaigns.map(row => ({ ...row, platform: db.stores.find(store => store.id === row.storeId)?.platform ?? '—', storeName: db.stores.find(store => store.id === row.storeId)?.name ?? row.storeId, spendDisplay: toDisplay(row.spend, row.currency) }))
}

export function adsImportRows(db: MockDatabase) {
  return adsData(db).imports.map(row => ({ ...row, spendDisplay: toDisplay(row.spend, 'USD') }))
}

export function recordAdImport(db: MockDatabase, fileName: string, actor: Actor) {
  requireActorPermission(actor, 'advertisement:import')

  const data = adsData(db)
  const row: AdsImportBatch = { id: `adimp-${data.imports.length + 1}`, fileName, platform: 'Amazon Ads', rows: 128, spend: minorFromDecimal('418.3600'), status: 'success', importedAt: new Date(actor.at).toLocaleString('sv-SE').slice(0, 16) }

  data.imports.unshift(row)

  const campaign = db.adsCampaigns[0]
  if (campaign)
    campaign.spend += row.spend
  writeAudit(db, actor, 'import_ads', 'ads_import', row.id, `导入广告花费文件 ${fileName}，解析 ${row.rows} 行。`)

  return row
}

export function adsPerformance(db: MockDatabase) {
  return adsCampaigns(db).map(row => ({ ...row, sales: Math.round(row.spend * 46 / 10), salesDisplay: toDisplay(Math.round(row.spend * 46 / 10), row.currency), roas: 4.6, salesSource: '已存储订单/利润结果' }))
}

export function allocationRows(db: MockDatabase) {
  return adsData(db).allocations.map(row => {
    const campaign = db.adsCampaigns.find(item => item.name === row.campaign)

    return { ...row, currency: campaign?.currency ?? 'USD', spendDisplay: toDisplay(row.spend, campaign?.currency ?? 'USD') }
  })
}

export interface AllocationShare { sku: string; ratio: number }

/**
 * 保存一个广告活动的完整分摊规则（替换该活动原有规则）。
 * 比例必须是正整数、SKU 不重复、合计恰好 100%；花费按整数万分位分摊，尾差给最后一行，保证合计等于活动花费。
 */
export function saveAllocation(db: MockDatabase, campaignId: string, shares: AllocationShare[], actor: Actor) {
  requireActorPermission(actor, 'advertisement:write')

  const campaign = db.adsCampaigns.find(item => item.id === campaignId)
  if (!campaign || !shares.length)
    return null
  if (shares.some(item => !item.sku || !Number.isInteger(item.ratio) || item.ratio <= 0))
    return null
  if (new Set(shares.map(item => item.sku)).size !== shares.length)
    return null
  if (shares.reduce((sum, item) => sum + item.ratio, 0) !== 100)
    return null

  const data = adsData(db)
  const period = '2026-10'

  // 先撤回该活动旧规则对利润快照的影响，再写入新规则。
  for (const old of data.allocations.filter(row => row.campaign === campaign.name)) {
    const snapshot = db.profitSnapshots.find(item => item.internalSku === old.sku && item.storeId === campaign.storeId && item.period === period)
    if (snapshot) {
      snapshot.ads -= old.spend
      snapshot.profit += old.spend
    }
  }
  data.allocations = data.allocations.filter(row => row.campaign !== campaign.name)

  let allocated = 0

  const rows: AdsAllocation[] = shares.map((share, index) => {
    const spend = index === shares.length - 1 ? campaign.spend - allocated : Math.round(campaign.spend * share.ratio / 100)

    allocated += spend

    return { id: `alloc-${campaign.id}-${share.sku}`, campaign: campaign.name, sku: share.sku, ratio: share.ratio, spend, source: '广告分摊' }
  })

  for (const row of rows) {
    data.allocations.push(row)

    const snapshot = db.profitSnapshots.find(item => item.internalSku === row.sku && item.storeId === campaign.storeId && item.period === period)
    if (snapshot) {
      snapshot.ads += row.spend
      snapshot.profit -= row.spend
    }
  }
  writeAudit(db, actor, 'save_allocation', 'ads_allocation', campaign.id, `保存 ${campaign.name} 广告分摊规则：${rows.map(row => `${row.sku} ${row.ratio}%`).join('，')}。`)

  return rows
}

export function confirmFeeMap(db: MockDatabase, id: string, category: string, actor: Actor) {
  requireActorPermission(actor, 'integration:write')

  const row = financeData(db).feeMaps.find(item => item.id === id)
  if (!row)
    return
  row.category = category
  row.status = 'confirmed'
  writeAudit(db, actor, 'confirm_fee_map', 'fee_map', id, `人工确认费用映射为 ${category}。AI 仅提供建议。`)
  db.issues.filter(issue => issue.code === 'UNKNOWN_FEE_TYPE' && issue.status === 'open').forEach(issue => {
    issue.status = 'explained'
  })
}

export function handleIssue(db: MockDatabase, id: string, action: 'explained' | 'ignored', note: string, actor: Actor) {
  requireActorPermission(actor, 'report:write')

  const row = db.issues.find(item => item.id === id)
  if (!row)
    return
  row.status = action
  row.summary = note || row.summary
  writeAudit(db, actor, action, 'issue', id, note || `异常标记为 ${action}`)
}

export function createVoucherFromIssue(db: MockDatabase, issueId: string, actor: Actor) {
  requireActorPermission(actor, 'journal_entry:create')

  const issue = db.issues.find(item => item.id === issueId)
  if (!issue)
    return null
  const voucher: VoucherEntity = { id: nextId(db, 'vch'), no: `记-2026-11-${String(db.vouchers.length + 1).padStart(3, '0')}`, period: '2026-11', status: 'draft', debit: issue.amount, credit: issue.amount, currency: 'CNY', summary: `异常 ${issue.id} 处理凭证`, submitter: actor.name }

  db.vouchers.push(voucher)
  writeAudit(db, actor, 'create_voucher_draft', 'voucher', voucher.id, `从异常 ${issue.id} 创建凭证草稿。`)

  return voucher
}

export function createVoucherFromProfit(db: MockDatabase, actor: Actor) {
  requireActorPermission(actor, 'journal_entry:create')

  // 利润快照有多种币种，先按服务层汇率折算成凭证币种 CNY 再合计，不能直接相加。
  const total = db.profitSnapshots.filter(row => row.period === '2026-10').reduce((sum, row) => addMinor(sum, convertMinor(row.profit, row.currency, 'CNY')), 0)
  const amount: Minor = total || minorFromDecimal('100.0000')
  const voucher: VoucherEntity = { id: nextId(db, 'vch'), no: `记-2026-10-${String(db.vouchers.length + 1).padStart(3, '0')}`, period: '2026-10', status: 'draft', debit: amount, credit: amount, currency: 'CNY', summary: '10 月利润结转草稿', submitter: actor.name }

  db.vouchers.push(voucher)
  writeAudit(db, actor, 'create_voucher_draft', 'voucher', voucher.id, '从利润快照创建凭证草稿。')

  return voucher
}

export function submitVoucher(db: MockDatabase, voucherId: string, actor: Actor) {
  requireActorPermission(actor, 'journal_entry:submit')

  const voucher = db.vouchers.find(item => item.id === voucherId)
  if (!voucher || (voucher.status !== 'draft' && voucher.status !== 'rejected'))
    return null
  const detail = voucherDetail(db, voucherId)
  if (!detail || !detail.balanced)
    return null
  voucher.status = 'pending'

  const approval = submitSuggestion(db, { title: voucher.summary, summary: '借贷合计由服务层校验，审批通过后才生成导出文件。', amount: minorToDecimal(voucher.debit), currency: voucher.currency, storeId: null, targetType: 'voucher', targetId: voucher.id }, actor)

  writeAudit(db, actor, 'submit_voucher', 'voucher', voucher.id, `提交凭证 ${voucher.no} 审批。`)

  return approval
}

export function createExportArtifact(db: MockDatabase, approvalId: string, voucherId: string, at: string) {
  const data = financeData(db)
  const existing = data.exports.find(item => item.approvalId === approvalId)
  if (existing)
    return existing
  const artifact = { id: `exp-${approvalId}`, fileName: `${voucherId}.xlsx`, approvalId, target: 'generic_xlsx', sha256: `sha256:${approvalId.slice(-8)}`, createdAt: at, status: 'available' }

  data.exports.push(artifact)

  return artifact
}

export function submitClearing(db: MockDatabase, ids: string[], actor: Actor) {
  requireActorPermission(actor, 'approval:create')

  const selected = clearingRows(db).filter(row => ids.includes(row.id))
  if (!selected.length)
    return null
  const difference = selected.reduce((sum, row) => sum + row.payoutAmount - row.arAmount, 0)
  if (difference !== 0)
    return null
  const amount = selected.reduce((sum, row) => sum + row.payoutAmount, 0)

  return submitSuggestion(db, { title: `核销 ${selected.map(row => row.payout).join('、')}`, summary: '多选打款与应收金额由服务层校验相等后提交审批。', amount: minorToDecimal(amount), currency: selected[0].currency as CurrencyCode, storeId: null, targetType: 'clearing', targetId: selected.map(row => row.id).join(',') }, actor)
}
