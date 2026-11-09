import type { CrmAccount, CrmAccountDetail } from '@/types/domain'

const accounts: CrmAccount[] = [
  { id: 'acc-alpine', name: 'Alpine Peak Distributors GmbH', type: '分销商', country: '德国', owner: '林夏', currency: 'EUR', pipeline: 48600, orders: 12, status: '合作中', tags: ['EU', '批发'] },
  { id: 'acc-ridge', name: 'Ridge & Co. Ltd', type: '分销商', country: '英国', owner: '林夏', currency: 'GBP', pipeline: 22400, orders: 7, status: '谈判中', tags: ['UK'] },
  { id: 'acc-summit', name: 'Summit Trail LLC', type: '批发客户', country: '美国', owner: '周衡', currency: 'USD', pipeline: 15200, orders: 4, status: '合作中', tags: ['US', '独立站'] },
  { id: 'acc-yiwu', name: '远足户外商贸', type: '渠道合作方', country: '中国', owner: '周衡', currency: 'CNY', pipeline: 180000, orders: 0, status: '线索转化', tags: ['国内', '义乌'] },
  { id: 'acc-pacific', name: 'Pacific Outdoor Brokerage', type: 'Broker', country: '新加坡', owner: '林夏', currency: 'USD', pipeline: 9600, orders: 1, status: '跟进中', tags: ['渠道'] },
]

const details: Record<string, CrmAccountDetail> = {
  'acc-alpine': {
    ...accounts[0],
    website: 'https://example.invalid/alpine',
    email: 'buyer@alpine.example',
    phone: '+49 89 0000 0000',
    note: '慕尼黑户外连锁的区域分销。不把亚马逊终端消费者建档。',
    contacts: [
      { name: 'Lena Vogel', title: '采购经理', email: 'lena@alpine.example' },
      { name: 'Jonas Kranz', title: '财务', email: 'ap@alpine.example' },
    ],
    opportunities: [
      { name: '2027 春季帐篷补货', amount: 28600, currency: 'EUR', stage: '报价' },
      { name: '睡袋试销', amount: 20000, currency: 'EUR', stage: '谈判' },
    ],
    relatedOrders: [
      { orderNo: 'PO-ALP-2026-09', amount: 18420, currency: 'EUR', date: '2026-09-12' },
    ],
    tickets: [
      { id: 't-19', subject: 'DE 站包装标签语言', status: '处理中' },
    ],
  },
  'acc-ridge': {
    ...accounts[1],
    website: 'https://example.invalid/ridge',
    email: 'hello@ridge.example',
    phone: '+44 20 0000 0000',
    note: '英国户外店渠道，正在谈 2026 Q4 睡袋。',
    contacts: [{ name: 'Amelia Shaw', title: 'Buyer', email: 'amelia@ridge.example' }],
    opportunities: [{ name: 'Q4 睡袋', amount: 22400, currency: 'GBP', stage: '谈判' }],
    relatedOrders: [],
    tickets: [],
  },
  'acc-summit': {
    ...accounts[2],
    website: 'https://example.invalid/summit',
    email: 'orders@summit.example',
    phone: '+1 415 000 0000',
    note: '独立站批发客户，对应 Shopify #10482。',
    contacts: [{ name: 'Chris Hale', title: 'Owner', email: 'chris@summit.example' }],
    opportunities: [{ name: '感恩节补货', amount: 15200, currency: 'USD', stage: '赢单' }],
    relatedOrders: [{ orderNo: '#10482', amount: 248, currency: 'USD', date: '2026-10-25' }],
    tickets: [{ id: 't-22', subject: '洛杉矶仓少发 1 盏灯', status: '待回复' }],
  },
  'acc-yiwu': {
    ...accounts[3],
    website: 'https://example.invalid/yiwu',
    email: 'sales@yiwu-outdoor.example',
    phone: '+86 579 0000 0000',
    note: '义乌渠道合作，尚未形成平台订单。',
    contacts: [{ name: '陈敏', title: '业务', email: 'chen@yiwu-outdoor.example' }],
    opportunities: [{ name: '国内团购帐篷', amount: 180000, currency: 'CNY', stage: '需求确认' }],
    relatedOrders: [],
    tickets: [],
  },
  'acc-pacific': {
    ...accounts[4],
    website: 'https://example.invalid/pacific',
    email: 'desk@pacific-broker.example',
    phone: '+65 0000 0000',
    note: '东南亚渠道经纪，只介绍批发客户，不持有库存。',
    contacts: [{ name: 'Priya Nair', title: 'Broker', email: 'priya@pacific-broker.example' }],
    opportunities: [{ name: '新加坡露营俱乐部', amount: 9600, currency: 'USD', stage: '线索' }],
    relatedOrders: [],
    tickets: [],
  },
}

export const crmAccounts = accounts
export const crmDetails = details
