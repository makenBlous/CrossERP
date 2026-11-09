import { database, delay } from '@/api/mock-client'

// 未来: GET /api/v1/account/tokens
export async function fetchTokens() {
  await delay()

  return database().db.accountTokens ?? []
}

// 未来: GET /api/v1/account/sessions
export async function fetchSessions() {
  await delay()

  return database().db.accountSessions ?? []
}

// 未来: GET /api/v1/account/profile
export async function fetchProfile() {
  await delay()

  return { name: '演示用户', email: 'demo@northwind.example', title: '跨境业务运营', timezone: 'Asia/Shanghai' }
}
