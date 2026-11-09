export type StatusDomain =
  | 'sales_order'
  | 'purchase_order'
  | 'receipt'
  | 'shipment'
  | 'stock_doc'
  | 'approval'
  | 'issue'
  | 'voucher'
  | 'stock_alert'
  | 'supplier'
  | 'crm'
  | 'generic'

export interface StatusDef {
  value: string
  zh: string
  en: string
  color: string
}

const row = (value: string, zh: string, en: string, color: string): StatusDef => ({ value, zh, en, color })

export const statusDictionary: Record<StatusDomain, StatusDef[]> = {
  sales_order: [
    row('paid', '待发货', 'Paid', 'info'),
    row('shipped', '已发货', 'Shipped', 'success'),
    row('partial_refund', '部分退款', 'Partial refund', 'warning'),
    row('refunded', '已退款', 'Refunded', 'error'),
    row('cancelled', '已取消', 'Cancelled', 'secondary'),
  ],
  purchase_order: [
    row('draft', '草稿', 'Draft', 'secondary'),
    row('submitted', '待审批', 'Submitted', 'warning'),
    row('approved', '已批准', 'Approved', 'info'),
    row('partial', '部分收货', 'Partial', 'primary'),
    row('received', '已收货', 'Received', 'success'),
    row('rejected', '已驳回', 'Rejected', 'error'),
  ],
  receipt: [
    row('posted', '已入账', 'Posted', 'success'),
    row('draft', '草稿', 'Draft', 'secondary'),
  ],
  shipment: [
    row('planned', '计划中', 'Planned', 'secondary'),
    row('in_transit', '在途', 'In transit', 'info'),
    row('arrived', '已签收', 'Arrived', 'success'),
  ],
  stock_doc: [
    row('draft', '草稿', 'Draft', 'secondary'),
    row('posted', '已过账', 'Posted', 'success'),
  ],
  approval: [
    row('pending', '待审批', 'Pending', 'warning'),
    row('approved', '已通过', 'Approved', 'success'),
    row('rejected', '已驳回', 'Rejected', 'error'),
  ],
  issue: [
    row('open', '待处理', 'Open', 'warning'),
    row('explained', '已说明', 'Explained', 'info'),
    row('ignored', '已忽略', 'Ignored', 'secondary'),
  ],
  voucher: [
    row('draft', '草稿', 'Draft', 'secondary'),
    row('pending', '待审批', 'Pending', 'warning'),
    row('posted', '已过账', 'Posted', 'success'),
  ],
  stock_alert: [
    row('ok', '正常', 'OK', 'success'),
    row('low', '偏低', 'Low', 'warning'),
    row('stockout', '断货', 'Stockout', 'error'),
  ],
  supplier: [
    row('active', '合作中', 'Active', 'success'),
    row('paused', '暂停', 'Paused', 'warning'),
  ],
  crm: [
    row('active', '合作中', 'Active', 'success'),
    row('negotiating', '谈判中', 'Negotiating', 'info'),
    row('follow_up', '跟进中', 'Follow up', 'warning'),
    row('converted', '线索转化', 'Converted', 'primary'),
  ],
  generic: [
    row('active', '启用', 'Active', 'success'),
    row('paused', '暂停', 'Paused', 'warning'),
    row('disabled', '停用', 'Disabled', 'secondary'),
  ],
}

const fallback: StatusDef = { value: '', zh: '', en: '', color: 'secondary' }

export function findStatus(domain: StatusDomain, value: string): StatusDef {
  return statusDictionary[domain].find(item => item.value === value) ?? { ...fallback, value, zh: value, en: value }
}

export function statusLabel(domain: StatusDomain, value: string, locale: 'zh-CN' | 'en'): string {
  const found = findStatus(domain, value)

  return locale === 'en' ? found.en : found.zh
}
