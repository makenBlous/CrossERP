import type { IssueRow, ProfitRow, ReconRun, StoreProfit, VoucherRow } from '@/types/domain'

export const profitRows: ProfitRow[] = [
  { sku: 'NW-TENT-2P', name: '双人帐篷', storeId: 'amz-us', storeName: 'Amazon US', currency: 'USD', revenue: 18640, platformFee: 2796, ads: 1480, firstMile: 2104, cost: 6240, profit: 6020 },
  { sku: 'NW-STOVE-01', name: '钛合金炉头', storeId: 'amz-us', storeName: 'Amazon US', currency: 'USD', revenue: 9240, platformFee: 1386, ads: 760, firstMile: 980, cost: 3120, profit: 2994 },
  { sku: 'NW-SLEEP-M', name: '羽绒睡袋', storeId: 'amz-uk', storeName: 'Amazon UK', currency: 'GBP', revenue: 5480, platformFee: 822, ads: 410, firstMile: 690, cost: 2140, profit: 1418 },
  { sku: 'NW-TENT-2P', name: '双人帐篷', storeId: 'amz-de', storeName: 'Amazon DE', currency: 'EUR', revenue: 8120, platformFee: 1299, ads: 540, firstMile: 870, cost: 2860, profit: 2551 },
  { sku: 'NW-LAMP-03', name: '营地灯', storeId: 'shopify', storeName: 'Shopify 独立站', currency: 'USD', revenue: 4360, platformFee: 174, ads: 320, firstMile: 410, cost: 1680, profit: 1776 },
  { sku: 'NW-BOTTLE-750', name: '钛杯', storeId: 'amz-de', storeName: 'Amazon DE', currency: 'EUR', revenue: 1960, platformFee: 294, ads: 80, firstMile: 210, cost: 720, profit: 656 },
]

export const storeProfits: StoreProfit[] = [
  { storeId: 'amz-us', storeName: 'Amazon US', currency: 'USD', revenue: 214320, platformFee: 32148, ads: 18640, firstMile: 22480, cost: 108212, profit: 32840 },
  { storeId: 'amz-uk', storeName: 'Amazon UK', currency: 'GBP', revenue: 68420, platformFee: 10947, ads: 4820, firstMile: 7310, cost: 36223, profit: 9120 },
  { storeId: 'amz-de', storeName: 'Amazon DE', currency: 'EUR', revenue: 79280, platformFee: 12685, ads: 5340, firstMile: 8120, cost: 42675, profit: 10460 },
  { storeId: 'shopify', storeName: 'Shopify 独立站', currency: 'USD', revenue: 66540, platformFee: 2662, ads: 4180, firstMile: 6920, cost: 43958, profit: 8820 },
]

export const reconRuns: ReconRun[] = [
  { id: 'recon-us-10', storeName: 'Amazon US', period: '2026-10', matched: 1284, unmatched: 38, matchRate: 97.12, status: '已完成', finishedAt: '2026-11-02 06:18 UTC' },
  { id: 'recon-uk-10', storeName: 'Amazon UK', period: '2026-10', matched: 412, unmatched: 20, matchRate: 95.37, status: '已完成', finishedAt: '2026-11-02 06:21 UTC' },
  { id: 'recon-de-10', storeName: 'Amazon DE', period: '2026-10', matched: 366, unmatched: 20, matchRate: 94.82, status: '已完成', finishedAt: '2026-11-02 06:24 UTC' },
  { id: 'recon-shop-10', storeName: 'Shopify 独立站', period: '2026-10', matched: 208, unmatched: 3, matchRate: 98.58, status: '已完成', finishedAt: '2026-11-02 06:26 UTC' },
  { id: 'recon-us-11', storeName: 'Amazon US', period: '2026-11 至今', matched: 240, unmatched: 16, matchRate: 93.75, status: '进行中', finishedAt: '2026-11-09 01:10 UTC' },
]

export const issues: IssueRow[] = [
  { id: 'iss-1008', code: 'AMOUNT_MISMATCH', severity: 'high', storeName: 'Amazon US', refNo: '114-8372615-2291846', amount: 12.4, currency: 'USD', status: '待处理', summary: '订单行净额与结算行相差 12.40 USD' },
  { id: 'iss-1014', code: 'UNKNOWN_FEE_TYPE', severity: 'medium', storeName: 'Amazon DE', refNo: 'STL-DE-2026-10-01', amount: 86.2, currency: 'EUR', status: '待处理', summary: '费用描述 "Digital Services Fee" 未映射' },
  { id: 'iss-1019', code: 'DUPLICATE_ROW', severity: 'high', storeName: 'Amazon UK', refNo: '204-9182736-4410982', amount: 64.99, currency: 'GBP', status: '待处理', summary: '同一订单行在结算文件中出现两次' },
  { id: 'iss-1022', code: 'SETTLEMENT_UNBALANCED', severity: 'high', storeName: 'Amazon US', refNo: 'STL-US-2026-10-02', amount: 318.55, currency: 'USD', status: '待处理', summary: '结算汇总行与明细合计不平' },
  { id: 'iss-1030', code: 'UNKNOWN_FEE_TYPE', severity: 'low', storeName: 'Shopify 独立站', refNo: 'POUT-10482', amount: 2.4, currency: 'USD', status: '已说明', summary: 'Shopify 调整项 "chargeback fee" 待归类' },
  { id: 'iss-1033', code: 'AMOUNT_MISMATCH', severity: 'medium', storeName: 'Amazon DE', refNo: '303-6621840-1182735', amount: 4.15, currency: 'EUR', status: '待处理', summary: '德站金额 119,00 与订单行 119.00 解析后仍差 4.15' },
  { id: 'iss-1041', code: 'DUPLICATE_ROW', severity: 'medium', storeName: 'Amazon US', refNo: 'ROW-88219', amount: 0, currency: 'USD', status: '已忽略', summary: '汇总行被误当成交易行，已标记不参与求和' },
  { id: 'iss-1044', code: 'SETTLEMENT_UNBALANCED', severity: 'high', storeName: 'Amazon UK', refNo: 'STL-UK-2026-10-01', amount: 22.08, currency: 'GBP', status: '待处理', summary: '打款总额与费用分类合计不平' },
]

export const vouchers: VoucherRow[] = [
  { id: 'vch-240', no: '记-2026-10-018', period: '2026-10', status: 'draft', debit: 42856.00, credit: 42856.00, currency: 'CNY', summary: '10 月 Amazon US 收入与费用草稿', submitter: '林夏' },
  { id: 'vch-241', no: '记-2026-10-019', period: '2026-10', status: 'pending', debit: 18640.20, credit: 18640.20, currency: 'CNY', summary: 'SKU NW-TENT-2P 成本结转，待财务审批', submitter: '林夏' },
  { id: 'vch-236', no: '记-2026-09-044', period: '2026-09', status: 'posted', debit: 96220.00, credit: 96220.00, currency: 'CNY', summary: '9 月四店利润结转，已过账', submitter: '周衡' },
  { id: 'vch-242', no: '记-2026-10-021', period: '2026-10', status: 'pending', debit: 3185.50, credit: 3185.50, currency: 'CNY', summary: '结算不平差额挂账建议，金额来自对账结果', submitter: '智能体建议' },
  { id: 'vch-228', no: '记-2026-08-031', period: '2026-08', status: 'posted', debit: 54110.00, credit: 54110.00, currency: 'CNY', summary: '8 月头程费用分摊', submitter: '周衡' },
]
