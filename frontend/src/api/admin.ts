import { assertPermission, database, delay } from '@/api/mock-client'
import type { Role } from '@/types/domain'

// 未来: GET /api/v1/admin/users
export async function fetchAdminUsers() {
  await delay()
  assertPermission('user_admin:read')

  const names = ['林夏', '周衡', '陈宁', 'Nina Wu', '王可', 'Ethan Li', '赵敏', '审计员']
  const roles = ['admin', 'operator', 'operator', 'finance', 'viewer', 'operator', 'finance', 'auditor']

  return names.map((name, index) => ({
    id: `usr-${index + 1}`,
    name,
    email: `${name.toLowerCase().replaceAll(' ', '.')}@northwind.example`,
    role: roles[index],
    status: index === 6 ? 'paused' : 'active',
    stores: index % 3 === 0 ? '全部店铺' : index % 2 === 0 ? 'Amazon US、Shopify' : 'Amazon UK、DE',
  }))
}

// 未来: GET /api/v1/admin/integrations
export async function fetchIntegrations() {
  await delay()
  assertPermission('integration:read')

  return database().db.adminIntegrations ?? []
}

// 未来: GET /api/v1/admin/modules
export async function fetchModules() {
  await delay()
  assertPermission('permission:read')

  return database().db.adminModules ?? []
}

// 未来: GET /api/v1/admin/roles
export async function fetchRoles() {
  await delay()
  assertPermission('permission:read')

  return ['admin', 'operator', 'finance', 'viewer', 'auditor'].map(role => ({ role, label: { admin: '管理员', operator: '运营', finance: '财务', viewer: '只读', auditor: '审计' }[role] }))
}

// 未来: GET /api/v1/admin/permissions
export async function fetchPermissions() {
  await delay()
  assertPermission('permission:read')

  return ['view', 'create', 'update', 'delete', 'approve', 'export', 'ship', 'receive', 'suggest'].map((code, index) => ({ id: `perm-${index + 1}`, code, name: { view: '查看', create: '新建', update: '修改', delete: '删除', approve: '审批', export: '导出', ship: '发货', receive: '收货', suggest: '提交建议' }[code] }))
}

// 未来: GET /api/v1/admin/dictionaries
export async function fetchDictionaries() {
  await delay()
  assertPermission('permission:read')

  return database().db.adminDicts ?? []
}

// 未来: GET /api/v1/admin/notifications
export async function fetchNotifications() {
  await delay()
  assertPermission('notification:read')

  return database().db.adminNotifications ?? []
}

// 未来: GET /api/v1/admin/settings
export async function fetchSettings() {
  await delay()
  assertPermission('permission:read')

  return database().db.adminSettings ?? []
}

// 未来: GET /api/v1/admin/role-overrides
export async function fetchRoleOverrides() {
  await delay()
  assertPermission('permission:read')

  return JSON.parse(JSON.stringify(database().db.roleOverrides ?? []))
}

// 未来: PUT /api/v1/admin/roles/{role}/visibility
export async function saveRoleVisibility(role: Role, hiddenGroups: string[], hiddenPageIds: string[]) {
  await delay()
  database().saveRoleOverride(role, hiddenGroups, hiddenPageIds, assertPermission('permission:write'))
}

// 未来: DELETE /api/v1/admin/roles/{role}/visibility
export async function resetRoleVisibility(role: Role) {
  await delay()
  database().resetRoleOverride(role, assertPermission('permission:write'))
}
