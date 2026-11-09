import { currentActor, database } from '@/api/mock-client'
import { writeAudit } from '@/mocks/services/audit'
import type { GapBAuditEvent, GapBChainNode, GapBDetail, GapBKey, GapBPageData, GapBRow } from '@/types/gap-b'

const now = '2026-11-10 10:00'
const gapAudit: GapBAuditEvent[] = []
let chainQuery = ''
let orderDraftCreated = false

function record(action: string, refType: string, refId: string, summary: string, channel?: string) {
  const actor = currentActor()
  const db = database()
  writeAudit(db.db, actor, action, refType, refId, summary)
  db.persist()
  const id = `gap-aud-${Date.now()}-${gapAudit.length}`
  gapAudit.unshift({ id, at: actor.at, actor: actor.name, action, refType, refId, summary, channel })
}

const titles: Record<GapBKey, [string, string]> = {
  S09: ['询价单', '向多家供应商询价并跟踪报价'],
  S10: ['询价比价', '并排比较报价，人工选择供应商后转采购单'],
  S11: ['采购合同', '合同、框架价与有效期'],
  S12: ['合同详情', '条款、价格表、附件与关联采购单'],
  S13: ['供应商评估', '准时率、合格率与价格稳定性'],
  I12: ['批次与效期', '按批次查看数量、生产日期和到期日'],
  I13: ['补货建议', '按安全库存和销量预测生成补货建议'],
  I14: ['调拨详情', '调出、在途、调入确认'],
  I15: ['盘点详情', '录入实盘数、查看差异并提交审批'],
  D05: ['业务链追溯', '从订单追溯到采购、库存、物流和凭证'],
  INT01: ['领星/赛狐导入向导', '选来源、上传、列映射、预览、导入'],
  INT02: ['平台同步', '查看平台同步任务和失败原因'],
  INT03: ['金蝶导出设置', '维护账套、凭证字和科目对照'],
  INT04: ['ERPNext 账套', '配置审批后的可选推送目标'],
  INT05: ['集成日志', '查看导入、同步和导出的结果'],
  W08: ['IM 审批卡片预览', '模拟飞书、企业微信和钉钉审批卡片'],
  SYS19: ['我的渠道绑定', '绑定和解绑个人 IM 身份'],
  SYS20: ['IM 审批设置', '配置通道、审批类型和金额门槛'],
  SYS25: ['通知渠道', '管理飞书、企业微信、钉钉、邮件和 Webhook'],
  SYS26: ['新增渠道', '配置渠道并测试发送'],
}

const state: Record<string, GapBRow[]> = {
  S09: [
    { id: 'rfq-001', no: 'RFQ-2026-001', subject: 'Q4 CN-1001 补货询价', supplierCount: 3, status: 'open', dueAt: '2026-11-15', amount: 240000, currency: 'CNY' },
    { id: 'rfq-002', no: 'RFQ-2026-002', subject: '英国站包装材料', supplierCount: 2, status: 'awarded', dueAt: '2026-11-08', amount: 85000, currency: 'CNY' },
  ],
  S10: [
    { id: 'rfq-001', no: 'RFQ-2026-001', quoteId: 'quote-001', supplier: '宁波星海供应链', unitPrice: 12000, qty: 20, total: 240000, currency: 'CNY', leadTime: '7 天', status: 'recommended' },
    { id: 'quote-002', no: 'RFQ-2026-001', quoteId: 'quote-002', supplier: '深圳远洋贸易', unitPrice: 12600, qty: 20, total: 252000, currency: 'CNY', leadTime: '5 天', status: 'quoted' },
    { id: 'quote-003', no: 'RFQ-2026-001', quoteId: 'quote-003', supplier: '义乌小商品', unitPrice: 11800, qty: 20, total: 236000, currency: 'CNY', leadTime: '14 天', status: 'quoted' },
  ],
  S11: [
    { id: 'contract-001', no: 'CON-2026-001', supplier: '宁波星海供应链', type: '框架采购', validFrom: '2026-01-01', validTo: '2026-12-31', status: 'active', amount: 1200000, currency: 'CNY' },
    { id: 'contract-002', no: 'CON-2026-002', supplier: '深圳远洋贸易', type: '包装材料', validFrom: '2026-03-01', validTo: '2026-12-01', status: 'expiring', amount: 350000, currency: 'CNY' },
  ],
  S13: [
    { id: 'score-001', supplier: '宁波星海供应链', onTime: '96%', qualified: '98%', priceStability: '92%', score: 95, trend: '+3.2' },
    { id: 'score-002', supplier: '深圳远洋贸易', onTime: '88%', qualified: '94%', priceStability: '86%', score: 89, trend: '-1.4' },
    { id: 'score-003', supplier: '义乌小商品', onTime: '82%', qualified: '91%', priceStability: '95%', score: 87, trend: '+0.8' },
  ],
  I12: [
    { id: 'batch-001', batchNo: 'B-2026-10-A', sku: 'CN-1001', warehouse: '华东 FBA', qty: 320, producedAt: '2026-10-01', expiresAt: '2028-10-01', status: 'ok' },
    { id: 'batch-002', batchNo: 'B-2025-12-C', sku: 'CN-1002', warehouse: '广州海外仓', qty: 46, producedAt: '2025-12-10', expiresAt: '2026-12-10', status: 'expiring' },
  ],
  I13: [
    { id: 'replenish-001', sku: 'CN-1001', warehouse: '华东 FBA', onHand: 42, safetyStock: 80, dailySales: 12, stockoutAt: '3.5 天', suggestedQty: 260, status: 'open' },
    { id: 'replenish-002', sku: 'CN-1002', warehouse: '广州海外仓', onHand: 130, safetyStock: 100, dailySales: 8, stockoutAt: '16 天', suggestedQty: 0, status: 'covered' },
  ],
  I14: [{ id: 'transfer-001', no: 'TR-2026-001', from: '华东 FBA', to: '广州海外仓', sku: 'CN-1001', qty: 80, status: 'in_transit', createdAt: now, movement: '待确认' }],
  I15: [{ id: 'count-001', no: 'CT-2026-001', warehouse: '华东 FBA', sku: 'CN-1001', bookQty: 320, actualQty: 317, variance: -3, status: 'pending', createdAt: now, approval: '待提交' }],
  D05: [],
  INT01: [{ id: 'import-001', source: '领星', fileName: 'lingxing-2026-11.csv', rows: 248, mapped: '12/12', status: 'ready', importedAt: now }],
  INT02: [{ id: 'sync-001', platform: 'Amazon US', type: '订单与库存', progress: '100%', status: 'succeeded', startedAt: now, message: '同步完成 248 行' }, { id: 'sync-002', platform: 'Shopify', type: '打款', progress: '42%', status: 'running', startedAt: now, message: '正在读取分页 3/7' }],
  INT05: [{ id: 'log-001', operation: '领星导入', target: 'import-001', status: 'succeeded', rows: 248, at: now }, { id: 'log-002', operation: 'Shopify 同步', target: 'sync-002', status: 'running', rows: 96, at: now }],
  W08: [{ id: 'im-3000', channel: '飞书', title: '费用报销 EX-2026-018', amount: 300000, currency: 'CNY', contentHash: 'sha256:8c7a…1b2e', threshold: '可在 IM 批准', status: 'pending' }, { id: 'im-80000', channel: '飞书', title: '付款申请 PAY-2026-004', amount: 8000000, currency: 'CNY', contentHash: 'sha256:9fd1…aa91', threshold: '超过 ¥50,000，去网页确认', status: 'web_required' }],
  SYS19: [{ id: 'binding-feishu', channel: '飞书', account: 'linxia@example.com', boundAt: '2026-10-01', status: 'bound' }, { id: 'binding-wecom', channel: '企业微信', account: '未绑定', boundAt: '-', status: 'unbound' }, { id: 'binding-dingtalk', channel: '钉钉', account: '未绑定', boundAt: '-', status: 'unbound' }],
  SYS20: [{ id: 'im-feishu', channel: '飞书', enabled: true, approvalTypes: '报销 / 采购 / 付款', threshold: 50000, callback: 'https://example.invalid/feishu/callback', signature: '已配置', status: 'active' }, { id: 'im-wecom', channel: '企业微信', enabled: false, approvalTypes: '报销', threshold: 50000, callback: '未配置', signature: '未配置', status: 'inactive' }],
  SYS25: [{ id: 'channel-feishu', channel: '飞书', capabilities: '消息 / 审批卡片 / 回调 / 身份绑定', enabled: true, configured: true, lastResult: '成功 · 2 分钟前' }, { id: 'channel-wecom', channel: '企业微信', capabilities: '消息 / 审批卡片 / 回调 / 身份绑定', enabled: true, configured: true, lastResult: '成功 · 1 小时前' }, { id: 'channel-dingtalk', channel: '钉钉', capabilities: '消息 / 审批卡片 / 回调 / 身份绑定', enabled: false, configured: false, lastResult: '未配置' }, { id: 'channel-email', channel: '邮件', capabilities: '消息', enabled: true, configured: true, lastResult: '成功 · 昨天' }],
}

const columns: Record<GapBKey, Array<{ key: string; title: string }>> = {
  S09: [{ key: 'no', title: '询价单号' }, { key: 'subject', title: '主题' }, { key: 'supplierCount', title: '供应商数' }, { key: 'dueAt', title: '截止日期' }, { key: 'status', title: '状态' }],
  S10: [{ key: 'supplier', title: '供应商' }, { key: 'unitPrice', title: '含税单价' }, { key: 'qty', title: '数量' }, { key: 'total', title: '报价总额' }, { key: 'leadTime', title: '交期' }, { key: 'status', title: '建议' }],
  S11: [{ key: 'no', title: '合同号' }, { key: 'supplier', title: '供应商' }, { key: 'type', title: '类型' }, { key: 'validTo', title: '有效期至' }, { key: 'status', title: '状态' }],
  S13: [{ key: 'supplier', title: '供应商' }, { key: 'onTime', title: '准时率' }, { key: 'qualified', title: '合格率' }, { key: 'priceStability', title: '价格稳定性' }, { key: 'score', title: '综合评分' }, { key: 'trend', title: '变化' }],
  I12: [{ key: 'batchNo', title: '批次' }, { key: 'sku', title: 'SKU' }, { key: 'warehouse', title: '仓库' }, { key: 'qty', title: '数量' }, { key: 'expiresAt', title: '到期日' }, { key: 'status', title: '状态' }],
  I13: [{ key: 'sku', title: 'SKU' }, { key: 'warehouse', title: '仓库' }, { key: 'onHand', title: '现有库存' }, { key: 'safetyStock', title: '安全库存' }, { key: 'stockoutAt', title: '预计断货' }, { key: 'suggestedQty', title: '建议补货量' }, { key: 'status', title: '状态' }],
  I14: [{ key: 'no', title: '调拨单号' }, { key: 'from', title: '调出仓' }, { key: 'to', title: '调入仓' }, { key: 'sku', title: 'SKU' }, { key: 'qty', title: '数量' }, { key: 'status', title: '状态' }],
  I15: [{ key: 'no', title: '盘点单号' }, { key: 'warehouse', title: '仓库' }, { key: 'sku', title: 'SKU' }, { key: 'bookQty', title: '账面' }, { key: 'actualQty', title: '实盘' }, { key: 'variance', title: '差异' }, { key: 'status', title: '状态' }],
  INT01: [{ key: 'source', title: '来源' }, { key: 'fileName', title: '文件' }, { key: 'rows', title: '行数' }, { key: 'mapped', title: '列映射' }, { key: 'status', title: '状态' }],
  INT02: [{ key: 'platform', title: '平台' }, { key: 'type', title: '同步内容' }, { key: 'progress', title: '进度' }, { key: 'status', title: '状态' }, { key: 'message', title: '结果' }],
  INT05: [{ key: 'operation', title: '操作' }, { key: 'target', title: '目标' }, { key: 'rows', title: '行数' }, { key: 'status', title: '状态' }, { key: 'at', title: '时间' }],
  W08: [{ key: 'channel', title: '渠道' }, { key: 'title', title: '审批事项' }, { key: 'amount', title: '金额' }, { key: 'threshold', title: '门槛' }, { key: 'status', title: '状态' }],
  SYS19: [{ key: 'channel', title: '渠道' }, { key: 'account', title: '外部账号' }, { key: 'boundAt', title: '绑定时间' }, { key: 'status', title: '状态' }],
  SYS20: [{ key: 'channel', title: '渠道' }, { key: 'approvalTypes', title: '可审批类型' }, { key: 'threshold', title: '网页确认门槛（分）' }, { key: 'signature', title: '签名配置' }, { key: 'status', title: '状态' }],
  SYS25: [{ key: 'channel', title: '渠道' }, { key: 'capabilities', title: '能力' }, { key: 'enabled', title: '启用' }, { key: 'configured', title: '配置' }, { key: 'lastResult', title: '最近结果' }],
  D05: [],
  S12: [],
  INT03: [],
  INT04: [],
  SYS26: [],
}

function detailFor(key: GapBKey, id: string): GapBDetail | undefined {
  if (key === 'S10')
    return { id, title: 'RFQ-2026-001 报价比较', status: 'open', summary: '三家供应商报价已收齐，选择后会生成采购单草稿。', fields: [{ label: '采购需求', value: 'CN-1001 × 20' }, { label: '历史最低价', value: '¥115.00 / 件（2026-09）' }, { label: '关联合同', value: 'CON-2026-001' }], steps: [{ id: 's1', title: '发布询价', detail: '已向 3 家供应商发送', status: 'done' }, { id: 's2', title: '比较报价', detail: '代码已计算含税总额与交期', status: 'open' }, { id: 's3', title: '转采购单', detail: orderDraftCreated ? 'PO-2026-001 草稿已生成（带 RFQ/合同来源）' : '必须由人选择供应商', status: orderDraftCreated ? 'done' : 'blocked' }], related: [{ id: 'rfq-001', type: '询价单', label: 'RFQ-2026-001', to: '/procurement/rfqs' }, { id: 'contract-001', type: '采购合同', label: 'CON-2026-001', to: '/procurement/contracts/contract-001' }, ...(orderDraftCreated ? [{ id: 'po-draft-rfq-001', type: '采购单草稿', label: 'PO-2026-001（RFQ-2026-001 / CON-2026-001）', to: '/procurement/orders' }] : [])] }
  if (key === 'S12')
    return { id, title: 'CON-2026-001 采购合同', status: 'active', summary: '框架采购合同，关键条款由人工确认后生效。', fields: [{ label: '供应商', value: '宁波星海供应链' }, { label: '有效期', value: '2026-01-01 至 2026-12-31' }, { label: '付款条件', value: '月结 30 天' }], steps: [{ id: 's1', title: '上传合同', detail: '合同原件已归档', status: 'done' }, { id: 's2', title: '人工确认条款', detail: 'AI 仅提供摘要，不改变条款', status: 'open' }], related: [{ id: 'po-1001', type: '采购单', label: 'PO-2026-001', to: '/procurement/orders/po-1001' }] }
  if (key === 'I14') {
    const row = state.I14.find(item => item.id === id)

    return { id, title: 'TR-2026-001 调拨详情', status: String(row?.status ?? 'in_transit'), summary: '调拨确认会产生调出和调入两条库存流水。', fields: [{ label: '调出仓', value: '华东 FBA' }, { label: '调入仓', value: '广州海外仓' }, { label: 'SKU / 数量', value: 'CN-1001 / 80' }, { label: '流水', value: String(row?.movement ?? '待确认') }], steps: [{ id: 's1', title: '创建调拨', detail: '草稿已保存', status: 'done' }, { id: 's2', title: '确认调出', detail: '库存流水 -80', status: row?.status === 'posted' ? 'done' : 'open' }, { id: 's3', title: '确认调入', detail: '在途入库后完成', status: row?.status === 'posted' ? 'done' : 'blocked' }], related: [{ id: 'mov-001', type: '库存流水', label: '查看调拨流水（-80 / +80）', to: '/inventory/movements' }] }
  }
  if (key === 'I15') {
    const row = state.I15.find(item => item.id === id)

    return { id, title: 'CT-2026-001 盘点详情', status: String(row?.status ?? 'pending'), summary: '差异过账前需提交盘点差异审批。', fields: [{ label: '仓库', value: '华东 FBA' }, { label: 'SKU', value: 'CN-1001' }, { label: '账面 / 实盘', value: `320 / ${row?.actualQty ?? 317}（差异 ${row?.variance ?? -3}）` }, { label: '审批', value: String(row?.approval ?? '待提交') }], steps: [{ id: 's1', title: '录入实盘', detail: '实盘数由人填写', status: 'done' }, { id: 's2', title: '提交差异审批', detail: '审批通过后才更新库存', status: row?.status === 'submitted' || row?.status === 'approved' || row?.status === 'posted' ? 'done' : 'open' }, { id: 's3', title: '过账', detail: row?.status === 'posted' ? '写入库存流水 -3' : '需审批后过账', status: row?.status === 'posted' ? 'done' : 'blocked' }], related: [{ id: 'approval-count-001', type: '审批', label: '盘点差异审批', to: '/approvals' }, ...(row?.status === 'posted' ? [{ id: 'count-mov-001', type: '库存流水', label: '盘亏 -3', to: '/inventory/movements' }] : [])] }
  }

  return undefined
}

export function getGapBPage(key: GapBKey, id?: string): GapBPageData {
  const [title, subtitle] = titles[key]
  const rows = state[key] ?? []
  const detail = id ? detailFor(key, id) : undefined
  const detailKeys: GapBKey[] = ['S10', 'S12', 'I14', 'I15']

  const chain: GapBChainNode[] = [
    { id: 'customer', title: '客户 / 商机', detail: 'Acme Europe · 赢单', status: 'connected', to: '/crm/accounts/acc-summit' },
    { id: 'order', title: '销售订单', detail: `SO-2026-001 · 客户和商机已关联${orderDraftCreated ? ' · 草稿已保存' : ''}`, status: 'connected', to: '/orders/ord-001' },
    { id: 'sku', title: 'SKU → 采购 → 入库', detail: 'CN-1001 · PO-2026-001 · 华东 FBA', status: 'connected', to: '/procurement/orders' },
    { id: 'logistics', title: '头程 / 出库 / 发货', detail: 'FBA 批次 FM-2026-004 · 运单已关联', status: 'connected', to: '/logistics/shipments/shp-001' },
    { id: 'voucher', title: '凭证', detail: 'VCH-2026-018 · 可回溯来源单据', status: 'connected', to: '/finance/vouchers' },
  ]

  return { key, title, subtitle, kind: detailKeys.includes(key) ? 'detail' : ['INT01', 'INT03', 'INT04', 'SYS20', 'SYS26'].includes(key) ? 'form' : 'list', columns: columns[key], rows: rows.map(row => ({ ...row })), detail, audit: gapAudit.slice(0, 20), chain: key === 'D05' ? chain : undefined }
}

export function applyGapBAction(key: GapBKey, action: string, payload: Record<string, string | number | boolean> = {}): string {
  if (action === 'create-rfq') {
    state.S09.unshift({ id: `rfq-${Date.now()}`, no: `RFQ-2026-${String(state.S09.length + 1).padStart(3, '0')}`, subject: String(payload.subject || '新建补货询价'), supplierCount: Number(payload.supplierCount || 2), status: 'open', dueAt: '2026-11-20', amount: Number(payload.amount || 120000), currency: 'CNY' })

    const id = state.S09[0].id
    record('create', 'request_for_quotation', String(id), '创建询价单草稿，等待人工发送')

    return '询价单草稿已创建，等待人工发送。已写入审计记录。'
  }
  if (action === 'award-rfq') {
    const quote = state.S10.find(item => item.id === String(payload.id)) ?? state.S10.find(item => item.status === 'recommended')
    state.S09[0].status = 'awarded'
    for (const row of state.S10)
      row.status = row.id === quote?.id ? 'recommended' : 'quoted'
    orderDraftCreated = true
    record('select_supplier', 'request_for_quotation', String(quote?.id ?? 'rfq-001'), `人工选择 ${String(quote?.supplier ?? '供应商')}，生成采购单草稿（rfq_id=RFQ-2026-001，contract_id=CON-2026-001）`)

    return '已选择供应商并生成采购单草稿（带 RFQ 与合同来源），采购单仍需人工审批。'
  }
  if (action === 'draft-replenishment') {
    const row = state.I13.find(item => item.id === String(payload.id))
    const qty = Number(row?.suggestedQty ?? 0)
    const mode = payload.mode === 'manual' ? '人工' : 'AI 建议'
    const id = `po-replenish-${Date.now()}`
    if (row) {
      row.status = 'drafted'
      row.purchaseOrderId = id
    }
    record('draft_purchase_order', 'purchase_order', id, `${mode}起草采购单，数量由安全库存与销量代码计算：${qty} 件；等待人工批准`)

    return `${mode}采购单草稿已保存（${qty} 件），等待人工批准。已写入审计记录。`
  }
  if (action === 'confirm-transfer') {
    const row = state.I14.find(item => item.id === String(payload.id))
    if (row) {
      row.status = 'posted'
      row.movement = '调出 -80；调入 +80'
      record('post', 'stock_transfer', String(row.id), '调拨已确认，生成调出 -80 与调入 +80 两条库存流水')
    }

    return '调拨已确认，调出和调入库存流水均已记录。已写入审计记录。'
  }
  if (action === 'submit-count') {
    const row = state.I15.find(item => item.id === String(payload.id))
    if (row) {
      row.status = 'submitted'
      row.approval = '待审批'
      row.actualQty = Number(payload.actualQty ?? row.actualQty ?? 317)
      row.variance = Number(row.actualQty) - Number(row.bookQty)
      record('submit', 'stock_count', String(row.id), `提交盘点差异审批，差异 ${row.variance}，审批通过前不改库存`)
    }

    return '盘点差异已提交审批，审批通过前不会改变库存。已写入审计记录。'
  }
  if (action === 'approve-count') {
    const row = state.I15.find(item => item.id === String(payload.id))
    if (!row || row.status !== 'submitted')
      return '只有已提交的盘点差异才能审批。'
    row.status = 'posted'
    row.approval = '已批准并过账'
    record('approve', 'stock_count', String(row.id), `盘点差异已批准并过账，库存流水 ${row.variance} 件`)

    return `盘点差异已批准，库存按代码更新 ${row.variance} 件。已写入审计记录。`
  }
  if (action === 'upload-import') {
    state.INT01[0].status = 'mapped'
    record('upload', 'integration_import', 'import-001', '上传领星/赛狐文件，生成 AI 列映射建议，等待人工确认')

    return '文件已上传，建议列映射已生成，请人工确认。'
  }
  if (action === 'confirm-import') {
    state.INT01[0].status = 'imported'
    record('confirm_mapping', 'integration_import', 'import-001', '人工确认列映射后导入，原始文件与映射版本可追溯')

    return '列映射已确认，导入完成并写入集成日志。'
  }
  if (action === 'preview-import') {
    state.INT01[0].status = 'previewed'
    record('preview', 'integration_import', 'import-001', '生成导入预览，金额与数量仍由确定性代码读取')

    return '预览已生成，请人工确认后导入。'
  }
  if (action === 'start-sync') {
    state.INT02.unshift({ id: `sync-${Date.now()}`, platform: String(payload.platform || 'Amazon US'), type: '订单与库存', progress: '0%', status: 'running', startedAt: now, message: '任务已创建' })

    record('start_sync', 'integration_sync', String(state.INT02[0].id), '创建平台同步任务，结果写入集成日志')

    return '同步任务已创建，已写入审计记录。'
  }
  if (action === 'save-settings') {
    record('update', keyToRefType(key), key, '设置已保存，敏感配置只显示「已配置」')

    return '设置已保存，敏感配置只显示「已配置」。已写入审计记录。'
  }
  if (action === 'approve-im') {
    const row = state.W08.find(item => item.id === String(payload.id))
    if (!row)
      return '找不到审批卡片。'
    if (Number(row.amount) > 5000000)
      return '金额超过 IM 门槛，只能去网页确认。'
    row.status = 'approved'
    record('approve', 'im_approval', String(row.id), '通过 IM 审批，内容哈希校验通过', '飞书')

    return '已通过 IM 审批，审计渠道记录为飞书。'
  }
  if (action === 'reject-im') {
    const row = state.W08.find(item => item.id === String(payload.id))
    if (row) {
      row.status = 'rejected'
      record('reject', 'im_approval', String(row.id), '驳回 IM 审批卡片', '飞书')
    }

    return '已驳回 IM 审批卡片，审计渠道记录为飞书。'
  }
  if (action === 'tamper-im') {
    const row = state.W08.find(item => item.id === String(payload.id))
    if (row) {
      row.status = 'tampered'
      record('blocked', 'im_approval', String(row.id), '内容哈希不一致，阻止 IM 审批操作', '飞书')
    }

    return '内容哈希不一致，卡片已阻止操作。'
  }
  if (action === 'bind-channel') {
    const row = state.SYS19.find(item => item.id === String(payload.id))
    if (row) {
      row.status = 'bound'
      row.account = String(payload.account || 'demo@example.com')
      row.boundAt = now.slice(0, 10)
      record('bind', 'channel_binding', String(row.id), `绑定${row.channel}身份 ${row.account}`)
    }

    return '渠道身份已绑定。'
  }
  if (action === 'unbind-channel') {
    const row = state.SYS19.find(item => item.id === String(payload.id))
    if (row) {
      row.status = 'unbound'
      row.account = '未绑定'
      row.boundAt = '-'
      record('unbind', 'channel_binding', String(row.id), `解绑${row.channel}身份`)
    }

    return '渠道已解绑。'
  }
  if (action === 'test-channel') {
    const row = state.SYS25.find(item => item.id === String(payload.id))
    if (row)
      row.lastResult = '测试成功 · 刚刚'
    record('test_send', 'notification_channel', String(payload.id ?? 'new'), `测试${String(payload.channel ?? row?.channel ?? '渠道')}发送成功`)

    return '测试消息已发送，返回成功。已写入审计记录。'
  }
  if (action === 'toggle-channel') {
    const row = state.SYS25.find(item => item.id === String(payload.id))
    if (row) {
      row.enabled = Boolean(payload.enabled)
      row.lastResult = row.enabled ? '已启用，等待下一次发送' : '已停用'
      record(row.enabled ? 'enable' : 'disable', 'notification_channel', String(row.id), `${row.channel}${row.enabled ? '启用' : '停用'}`)
    }

    return row?.enabled ? '渠道已启用。' : '渠道已停用。'
  }
  if (action === 'create-channel') {
    const id = `channel-${Date.now()}`
    state.SYS25.push({ id, channel: String(payload.channel || '钉钉'), capabilities: '消息 / 审批卡片 / 回调 / 身份绑定', enabled: false, configured: true, lastResult: '已配置，默认停用' })
    record('create', 'notification_channel', id, `新增${String(payload.channel || '钉钉')}渠道，密钥仅保存服务端引用，默认停用`)

    return '渠道已保存，默认停用。'
  }
  if (action === 'search-chain') {
    chainQuery = String(payload.query || '')
    record('trace', 'business_chain', chainQuery || 'SO-2026-001', `追溯 ${chainQuery || 'SO-2026-001'}，客户/商机、采购退货库存、物流双向链接均已校验`)

    return `已加载 ${chainQuery || 'SO-2026-001'} 业务链，4 个断点均已接通。已写入审计记录。`
  }

  if (action === 'win-opportunity') {
    orderDraftCreated = true
    record('create_order_draft', 'crm_opportunity', 'opp-acc-summit', '商机赢单，生成带 customer_id / opportunity_id 的销售订单草稿')

    return '商机已标记赢单，销售订单草稿已保存并带上客户/商机关联。'
  }

  return '操作已记录。'
}

function keyToRefType(key: GapBKey) {
  if (key.startsWith('INT'))
    return 'integration'
  if (key.startsWith('SYS'))
    return 'channel_setting'
  return 'gap_b'
}
