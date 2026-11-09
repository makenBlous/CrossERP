import { delay } from '@/api/mock-client'
import { applyGapBAction, getGapBPage } from '@/mocks/services/gap-b'
import type { GapBKey, GapBPageData } from '@/types/gap-b'

// 未来: GET /api/v1/{module}/...，批次 B 静态原型统一从此 API 出口读取。
export async function fetchGapBPage(key: GapBKey, id?: string): Promise<GapBPageData> {
  await delay()

  return getGapBPage(key, id)
}

// 未来: POST/PATCH /api/v1/{module}/...，所有写操作均经过服务层审计。
export async function submitGapBAction(key: GapBKey, action: string, payload: Record<string, string | number | boolean> = {}): Promise<string> {
  await delay()

  return applyGapBAction(key, action, payload)
}
