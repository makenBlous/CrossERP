import { assertPermission, database, delay } from '@/api/mock-client'
import { projectCalendar, projectPeriods, projectTodos } from '@/mocks/project-ops'
import { projectDashboard, projectStores } from '@/mocks/project'

// 未来: GET /api/v1/stores
export async function fetchStores() {
  await delay()
  assertPermission('report:read')

  return projectStores(database().db)
}

// 未来: GET /api/v1/dashboard?store_id=&period=
export async function fetchDashboard(storeId = 'all', period = '2026-10') {
  await delay()
  assertPermission('report:read')

  return projectDashboard(database().db, storeId, period)
}

// 未来: GET /api/v1/dashboard/periods
export async function fetchPeriods() {
  await delay()
  assertPermission('report:read')

  return projectPeriods(database().db)
}

// 未来: GET /api/v1/dashboard/todos
export async function fetchTodos() {
  await delay()
  assertPermission('report:read')

  return projectTodos(database().db)
}

// 未来: GET /api/v1/dashboard/calendar
export async function fetchCalendar() {
  await delay()
  assertPermission('report:read')

  return projectCalendar(database().db)
}
