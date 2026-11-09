import type { Store } from '@/types/domain'

export const stores: Store[] = [
  { id: 'amz-us', name: 'Northwind Outdoor US', platform: 'Amazon', marketplace: 'US', currency: 'USD' },
  { id: 'amz-uk', name: 'Northwind Outdoor UK', platform: 'Amazon', marketplace: 'UK', currency: 'GBP' },
  { id: 'amz-de', name: 'Northwind Outdoor DE', platform: 'Amazon', marketplace: 'DE', currency: 'EUR' },
  { id: 'shopify', name: 'northwind-outdoor.com', platform: 'Shopify', marketplace: '独立站', currency: 'USD' },
]
