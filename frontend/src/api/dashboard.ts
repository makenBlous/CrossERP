import { database, delay } from '@/api/mock-client'
import { projectCalendar, projectPeriods, projectTodos } from '@/mocks/project-ops'
import { projectDashboard, projectStores } from '@/mocks/project'

// 未来: GET /api/v1/stores
export async function fetchStores() {
  await delay()

  return projectStores(database().db)
}

// 未来: GET /api/v1/dashboard?store_id=&period=
export async function fetchDashboard(storeId = 'all', period = '2026-10') {
  await delay()

  return projectDashboard(database().db, storeId, period)
}

// 未来: GET /api/v1/dashboard/periods
export async function fetchPeriods() {
  await delay()

  return projectPeriods(database().db)
}

// 未来: GET /api/v1/dashboard/todos
export async function fetchTodos() {
  await delay()

  return projectTodos(database().db)
}

// 未来: GET /api/v1/dashboard/calendar
export async function fetchCalendar() {
  await delay()

  return projectCalendar(database().db)
}
