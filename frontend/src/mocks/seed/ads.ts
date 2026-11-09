import type { MockDatabase } from '@/types/entities'
import { minorFromDecimal } from '@/utils/money'

export function seedAds(db: MockDatabase) {
  const campaign = db.adsCampaigns[0]
  const sku = db.skus[0]?.internalSku ?? 'TENT-2P'
  const seededSpend = campaign ? Math.round(campaign.spend / 2) : 0

  db.ads = {
    imports: [
      { id: 'adimp-1', fileName: 'amazon-ads-2026-10.csv', platform: 'Amazon Ads', rows: 1240, spend: minorFromDecimal('3680.4200'), status: 'success', importedAt: '2026-11-01 10:12' },
      { id: 'adimp-2', fileName: 'shopify-meta-2026-10.csv', platform: 'Meta', rows: 382, spend: minorFromDecimal('924.1800'), status: 'success', importedAt: '2026-11-01 10:20' },
    ],
    allocations: campaign ? [{ id: 'alloc-seed-1', campaign: campaign.name, sku, ratio: 50, spend: seededSpend, source: '广告分摊' }] : [],
  }
  const snapshot = db.profitSnapshots.find(item => item.internalSku === sku && item.period === '2026-10')
  if (snapshot) {
    snapshot.ads += seededSpend
    snapshot.profit -= seededSpend
  }
}
