import { assertCan, delay } from '@/api/mock-client'
import { applyGapBAction, getGapBPage } from '@/mocks/services/gap-b'
import type { GapBKey, GapBPageData } from '@/types/gap-b'

const actionPermissions: Record<string, Parameters<typeof assertCan>[0]> = {
  'create-rfq': 'create',
  'award-rfq': 'update',
  'draft-replenishment': 'create',
  'confirm-transfer': 'update',
  'submit-count': 'update',
  'approve-count': 'approve',
  'upload-import': 'update',
  'preview-import': 'update',
  'confirm-import': 'update',
  'start-sync': 'update',
  'save-settings': 'update',
  'save-attachment': 'update',
  'approve-im': 'approve',
  'reject-im': 'approve',
  'tamper-im': 'update',
  'bind-channel': 'update',
  'unbind-channel': 'update',
  'test-channel': 'update',
  'toggle-channel': 'update',
  'create-channel': 'create',
  'search-chain': 'update',
  'win-opportunity': 'create',
}

// 未来: GET /api/v1/{module}/...，批次 B 静态原型统一从此 API 出口读取。
export async function fetchGapBPage(key: GapBKey, id?: string): Promise<GapBPageData> {
  await delay()

  return getGapBPage(key, id)
}

// 未来: POST/PATCH /api/v1/{module}/...，所有写操作均经过服务层审计。
export async function submitGapBAction(key: GapBKey, action: string, payload: Record<string, string | number | boolean> = {}): Promise<string> {
  await delay()

  const permission = actionPermissions[action]

  if (permission)
    assertCan(permission)

  return applyGapBAction(key, action, payload)
}
