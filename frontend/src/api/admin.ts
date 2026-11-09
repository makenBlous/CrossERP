import { currentActor, database, delay } from '@/api/mock-client'
import type { Role } from '@/types/domain'
import { writeAudit } from '@/mocks/services/audit'

// 未来: GET /api/v1/admin/users
export async function fetchAdminUsers() {
  await delay()

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

// 未来: PATCH /api/v1/admin/notifications/{id}
export async function updateNotification(id: string, enabled: boolean) {
  await delay()

  const actor = currentActor()
  if (actor.role !== 'admin')
    throw new Error('只有管理员可以修改通知规则')
  const item = (database().db.adminNotifications ?? []).find(row => row.id === id)
  if (!item)
    throw new Error('通知规则不存在')
  item.enabled = enabled
  writeAudit(database().db, actor, 'admin.notification.updated', 'notification_rule', id, `${item.event}：${enabled ? '启用' : '停用'}`)
  database().persist()

  return item
}

// 未来: GET /api/v1/admin/settings
export async function fetchSettings() {
  await delay()

  return database().db.adminSettings ?? []
}

// 未来: GET /api/v1/admin/role-overrides
export async function fetchRoleOverrides() {
  await delay()

  return JSON.parse(JSON.stringify(database().db.roleOverrides ?? []))
}

// 未来: PUT /api/v1/admin/roles/{role}/visibility
export async function saveRoleVisibility(role: Role, hiddenGroups: string[], hiddenPageIds: string[]) {
  await delay()
  database().saveRoleOverride(role, hiddenGroups, hiddenPageIds, currentActor())
}

// 未来: DELETE /api/v1/admin/roles/{role}/visibility
export async function resetRoleVisibility(role: Role) {
  await delay()
  database().resetRoleOverride(role, currentActor())
}
