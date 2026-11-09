import { database, delay } from '@/api/mock-client'

// 未来: GET /api/v1/admin/users
export async function fetchAdminUsers() {
  await delay()

  return database().db.agentDefinitions.map((item, index) => ({ id: `usr-${index + 1}`, name: ['林夏', '周衡', '审计员'][index % 3], email: `${item.id}@northwind.example`, role: ['admin', 'operator', 'auditor'][index % 3], status: item.status, stores: '全部店铺' }))
}

// 未来: GET /api/v1/admin/integrations
export async function fetchIntegrations() {
  await delay()

  return database().db.adminIntegrations ?? []
}

// 未来: GET /api/v1/admin/modules
export async function fetchModules() {
  await delay()

  return database().db.adminModules ?? []
}

// 未来: GET /api/v1/admin/roles
export async function fetchRoles() {
  await delay()

  return ['admin', 'operator', 'finance', 'viewer', 'auditor'].map(role => ({ role, label: { admin: '管理员', operator: '运营', finance: '财务', viewer: '只读', auditor: '审计' }[role] }))
}

// 未来: GET /api/v1/admin/permissions
export async function fetchPermissions() {
  await delay()

  return ['view', 'create', 'update', 'delete', 'approve', 'export', 'ship', 'receive', 'suggest'].map((code, index) => ({ id: `perm-${index + 1}`, code, name: { view: '查看', create: '新建', update: '修改', delete: '删除', approve: '审批', export: '导出', ship: '发货', receive: '收货', suggest: '提交建议' }[code] }))
}

// 未来: GET /api/v1/admin/dictionaries
export async function fetchDictionaries() {
  await delay()

  return database().db.adminDicts ?? []
}

// 未来: GET /api/v1/admin/notifications
export async function fetchNotifications() {
  await delay()

  return database().db.adminNotifications ?? []
}

// 未来: GET /api/v1/admin/settings
export async function fetchSettings() {
  await delay()

  return database().db.adminSettings ?? []
}
