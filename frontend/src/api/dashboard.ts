import { assertPermission, currentActor, database, delay } from '@/api/mock-client'
import { projectCalendar, projectPeriods, projectTodos } from '@/mocks/project-ops'
import { projectDashboard, projectStores } from '@/mocks/project'
import { projectMyDashboard, projectMyTodos } from '@/mocks/services/home'
import { useSessionStore } from '@/stores/session'
import { roleSubject } from '@/utils/permission-engine'

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

/** 首页经营总览：服务层按当前主体允许的店铺集合裁剪。 */
export async function fetchMyDashboard(storeId = 'all', period = '2026-10') {
  await delay()

  const session = useSessionStore()

  return projectMyDashboard(database().db, roleSubject(session.role, session.userId), storeId, period)
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

/** 首页个人待办：只返回当前用户作为负责人或处理人的记录。 */
export async function fetchMyTodos() {
  await delay()

  const session = useSessionStore()

  return projectMyTodos(database().db, roleSubject(session.role, session.userId), session.userId, currentActor().name)
}

// 未来: GET /api/v1/dashboard/calendar
export async function fetchCalendar() {
  await delay()
  assertPermission('report:read')

  return projectCalendar(database().db)
}
