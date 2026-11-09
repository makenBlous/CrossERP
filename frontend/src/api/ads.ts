import { assertCan, database, delay, readMock } from '@/api/mock-client'
import { type AllocationShare, adsCampaigns, adsImportRows, adsPerformance, allocationRows, recordAdImport, saveAllocation } from '@/mocks/services/finance'

export async function fetchAdCampaigns() {
  await delay()

  return readMock(adsCampaigns(database().db))
}
export async function fetchAdImports() {
  await delay()

  return readMock(adsImportRows(database().db))
}
export async function fetchAdPerformance() {
  await delay()

  return readMock(adsPerformance(database().db))
}
export async function fetchAllocations() {
  await delay()

  return readMock(allocationRows(database().db))
}
export async function saveAdAllocation(campaignId: string, shares: AllocationShare[]) {
  const actor = assertCan('update')
  const rows = saveAllocation(database().db, campaignId, shares, actor)

  if (rows)
    database().persist()

  return readMock(rows ? allocationRows(database().db) : null)
}

export async function uploadAdImport(fileName: string) {
  const actor = assertCan('create')
  const row = recordAdImport(database().db, fileName, actor)

  database().persist()

  if (!row)
    throw new Error('广告导入未创建')

  const projected = adsImportRows(database().db).find(item => item.id === row.id)
  if (!projected)
    throw new Error('广告导入记录未找到')

  return readMock(projected)
}
