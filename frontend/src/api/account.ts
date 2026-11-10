import { assertPermission, database, delay } from '@/api/mock-client'
import { changePassword as changePasswordService, listTokens } from '@/mocks/services/crm-admin'

// 未来: GET /api/v1/account/tokens
export async function fetchTokens() {
  await delay()

  const actor = assertPermission('user:read')

  return listTokens(database().db, actor)
}

// 未来: GET /api/v1/account/sessions
export async function fetchSessions() {
  await delay()
  assertPermission('user:read')

  return database().db.accountSessions ?? []
}

// 未来: GET /api/v1/account/profile
export async function fetchProfile() {
  await delay()
  assertPermission('user:read')

  return { name: '演示用户', email: 'demo@northwind.example', title: '跨境业务运营', timezone: 'Asia/Shanghai' }
}

// 未来: POST /api/v1/account/tokens
export async function createAccountToken(name: string) {
  await delay()

  const actor = assertPermission('user:write')

  return database().createToken(name, actor)
}

// 未来: POST /api/v1/account/tokens/{id}/revoke
export async function revokeAccountToken(id: string) {
  await delay()

  const actor = assertPermission('user:write')

  return database().revokeToken(id, actor)
}

// 未来: POST /api/v1/account/password
export async function changePassword() {
  await delay()

  const actor = assertPermission('user:write')

  changePasswordService(database().db, actor)
  database().persist()
}
