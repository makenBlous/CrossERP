import type { DashboardPayload } from '@/types/domain'

export const dashboardAll: DashboardPayload = {
  periodLabel: '2026-10-01 ~ 2026-10-31',
  kpi: {
    sales: 428560,
    netProfit: 61240,
    grossMargin: 31.4,
    refundRate: 4.8,
    matchRate: 96.2,
    openIssues: 18,
    pendingApprovals: 5,
    currency: 'USD',
  },
  trend: [
    { month: '2026-06', sales: 352100, profit: 48620 },
    { month: '2026-07', sales: 371840, profit: 51210 },
    { month: '2026-08', sales: 398220, profit: 54880 },
    { month: '2026-09', sales: 384760, profit: 50140 },
    { month: '2026-10', sales: 428560, profit: 61240 },
    { month: '2026-11', sales: 126480, profit: 17320 },
  ],
  stores: [
    { storeId: 'amz-us', storeName: 'Northwind Outdoor US', platform: 'Amazon', marketplace: 'US', sales: 214320, profit: 32840, matchRate: 97.1, currency: 'USD' },
    { storeId: 'amz-uk', storeName: 'Northwind Outdoor UK', platform: 'Amazon', marketplace: 'UK', sales: 68420, profit: 9120, matchRate: 95.4, currency: 'GBP' },
    { storeId: 'amz-de', storeName: 'Northwind Outdoor DE', platform: 'Amazon', marketplace: 'DE', sales: 79280, profit: 10460, matchRate: 94.8, currency: 'EUR' },
    { storeId: 'shopify', storeName: 'northwind-outdoor.com', platform: 'Shopify', marketplace: '独立站', sales: 66540, profit: 8820, matchRate: 98.6, currency: 'USD' },
  ],
  reasons: [
    { code: 'AMOUNT_MISMATCH', count: 7 },
    { code: 'UNKNOWN_FEE_TYPE', count: 5 },
    { code: 'DUPLICATE_ROW', count: 3 },
    { code: 'SETTLEMENT_UNBALANCED', count: 3 },
  ],
}

export const dashboardByStore: Record<string, DashboardPayload> = {
  'all': dashboardAll,
  'amz-us': {
    periodLabel: '2026-10-01 ~ 2026-10-31',
    kpi: { sales: 214320, netProfit: 32840, grossMargin: 33.1, refundRate: 3.9, matchRate: 97.1, openIssues: 6, pendingApprovals: 2, currency: 'USD' },
    trend: [
      { month: '2026-06', sales: 176400, profit: 24880 },
      { month: '2026-07', sales: 188220, profit: 27140 },
      { month: '2026-08', sales: 201560, profit: 29410 },
      { month: '2026-09', sales: 194880, profit: 26820 },
      { month: '2026-10', sales: 214320, profit: 32840 },
      { month: '2026-11', sales: 64210, profit: 9140 },
    ],
    stores: [dashboardAll.stores[0]],
    reasons: [
      { code: 'AMOUNT_MISMATCH', count: 3 },
      { code: 'UNKNOWN_FEE_TYPE', count: 2 },
      { code: 'DUPLICATE_ROW', count: 1 },
    ],
  },
  'amz-uk': {
    periodLabel: '2026-10-01 ~ 2026-10-31',
    kpi: { sales: 68420, netProfit: 9120, grossMargin: 28.6, refundRate: 5.1, matchRate: 95.4, openIssues: 5, pendingApprovals: 1, currency: 'USD' },
    trend: [
      { month: '2026-06', sales: 54200, profit: 7040 },
      { month: '2026-07', sales: 58110, profit: 7680 },
      { month: '2026-08', sales: 62340, profit: 8210 },
      { month: '2026-09', sales: 59880, profit: 7440 },
      { month: '2026-10', sales: 68420, profit: 9120 },
      { month: '2026-11', sales: 18440, profit: 2360 },
    ],
    stores: [dashboardAll.stores[1]],
    reasons: [
      { code: 'DUPLICATE_ROW', count: 2 },
      { code: 'SETTLEMENT_UNBALANCED', count: 2 },
      { code: 'AMOUNT_MISMATCH', count: 1 },
    ],
  },
  'amz-de': {
    periodLabel: '2026-10-01 ~ 2026-10-31',
    kpi: { sales: 79280, netProfit: 10460, grossMargin: 29.2, refundRate: 6.4, matchRate: 94.8, openIssues: 5, pendingApprovals: 1, currency: 'USD' },
    trend: [
      { month: '2026-06', sales: 61220, profit: 8020 },
      { month: '2026-07', sales: 64880, profit: 8460 },
      { month: '2026-08', sales: 70110, profit: 9180 },
      { month: '2026-09', sales: 67440, profit: 8320 },
      { month: '2026-10', sales: 79280, profit: 10460 },
      { month: '2026-11', sales: 22180, profit: 2860 },
    ],
    stores: [dashboardAll.stores[2]],
    reasons: [
      { code: 'UNKNOWN_FEE_TYPE', count: 3 },
      { code: 'AMOUNT_MISMATCH', count: 2 },
    ],
  },
  'shopify': {
    periodLabel: '2026-10-01 ~ 2026-10-31',
    kpi: { sales: 66540, netProfit: 8820, grossMargin: 34.8, refundRate: 2.1, matchRate: 98.6, openIssues: 2, pendingApprovals: 1, currency: 'USD' },
    trend: [
      { month: '2026-06', sales: 60280, profit: 8680 },
      { month: '2026-07', sales: 60630, profit: 7930 },
      { month: '2026-08', sales: 64210, profit: 8080 },
      { month: '2026-09', sales: 62560, profit: 7560 },
      { month: '2026-10', sales: 66540, profit: 8820 },
      { month: '2026-11', sales: 21650, profit: 2960 },
    ],
    stores: [dashboardAll.stores[3]],
    reasons: [
      { code: 'UNKNOWN_FEE_TYPE', count: 1 },
      { code: 'AMOUNT_MISMATCH', count: 1 },
    ],
  },
}
