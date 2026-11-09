/* eslint-disable indent */
import { legacyPermissionKeys, legacyRoleActions, permissionCatalog, roleTemplates } from '@/config/permissions'
import type { Role } from '@/types/domain'
import type { DataScopeRuleType, EffectivePermission, PermissionSubject, RolePermission } from '@/types/foundation'
import type { FieldAccess } from '@/types/gap-c'

const templateById = new Map(roleTemplates.map(item => [item.id, item]))
const legacyRoles = ['admin', 'operator', 'finance', 'viewer', 'auditor'] as const
type LegacyRole = typeof legacyRoles[number]

const legacyDefaultDataScopes: Record<LegacyRole, DataScopeRuleType[]> = {
  admin: ['all'],
  operator: ['store', 'owner'],
  finance: ['all'],
  viewer: ['store'],
  auditor: ['all'],
}

// 依据 02 设计：老板/总经理无字段限制；财务覆盖全部财务数据，但员工薪资、证件和银行卡仍隐藏。
const legacySensitiveFieldPermissions: Record<LegacyRole, string[]> = {
  admin: ['sku.cost:read', 'sku.margin:read', 'employee.salary:read', 'salary_slip:read_all', 'employee.id_number:read', 'employee.bank_account:read'],
  operator: [],
  finance: ['sku.cost:read', 'sku.margin:read'],
  viewer: [],
  auditor: [],
}

/** 敏感字段的唯一登记表；新增敏感字段必须先登记权限点。 */
export const sensitiveFieldPermissionKeys: Record<string, string> = {
  cost: 'sku.cost:read',
  margin: 'sku.margin:read',
  salary: 'employee.salary:read',
  salaryDetail: 'salary_slip:read_all',
  idCard: 'employee.id_number:read',
  bankAccount: 'employee.bank_account:read',
  buyerContact: 'buyer.contact:read',
}

function legacyAllowsAction(role: typeof legacyRoles[number], action: string) {
  const actions = legacyRoleActions[role]
  if (actions.includes(action))
    return true
  if (action === 'write' && actions.includes('update'))
    return true
  if (action === 'submit' && (actions.includes('ship') || actions.includes('receive')))
    return true

  return action === 'create' && actions.includes('suggest')
}

function activeAt(startsAt?: string, expiresAt?: string, now = Date.now()) {
  return !(startsAt && Date.parse(startsAt) > now) && !(expiresAt && Date.parse(expiresAt) <= now)
}

function collectRoleIds(roleIds: string[], seen = new Set<string>()): string[] {
  for (const id of roleIds) {
    if (seen.has(id))
      continue
    seen.add(id)

    const role = templateById.get(id)
    if (role)
      collectRoleIds(role.parentIds, seen)
  }

  return [...seen]
}

function normalizePermissionSource(permission: RolePermission, roleId: string) {
  if (!permission.source || permission.source === '模板基础只读')
    return `角色 ${templateById.get(roleId)?.nameZh ?? roleId}`

  return permission.source
}

export function computeEffectivePermissions(subject: PermissionSubject, now = Date.now()): EffectivePermission[] {
  const permissions = new Map<string, { allows: string[]; denies: string[]; scopes: Set<DataScopeRuleType>; deniedScopes: Set<DataScopeRuleType> }>()

  const ensure = (key: string) => {
    const current = permissions.get(key)
    if (current)
      return current
    const created = { allows: [], denies: [], scopes: new Set<DataScopeRuleType>(), deniedScopes: new Set<DataScopeRuleType>() }

    permissions.set(key, created)

    return created
  }

  for (const roleId of collectRoleIds(subject.roleIds)) {
    const role = templateById.get(roleId)

    const rolePermissions: RolePermission[] = role?.permissions ?? (legacyRoles.includes(roleId as LegacyRole)
      ? [
          ...legacyRoleActions[roleId as LegacyRole].map(action => ({ permissionKey: legacyPermissionKeys[action], effect: 'allow' as const, source: `旧角色 ${roleId}` })),
          ...permissionCatalog
            .filter(point => (!point.sensitive && point.kind !== 'field' && point.key.endsWith(':read')) || legacySensitiveFieldPermissions[roleId as LegacyRole].includes(point.key) || (roleId === 'admin' && point.sensitive && point.kind !== 'field') || (roleId === 'operator' && point.key === 'permission:read') || (roleId === 'admin' && ['salary_slip:read_own', 'employee_record:read_own'].includes(point.key)) || legacyAllowsAction(roleId as LegacyRole, point.key.split(':')[1] ?? ''))
            .map(point => ({ permissionKey: point.key, effect: 'allow' as const, source: `旧角色 ${roleId}` })),
        ]
      : [])

    for (const permission of rolePermissions) {
      const target = ensure(permission.permissionKey)
      const source = normalizePermissionSource(permission, roleId)
      if (permission.effect === 'deny') {
        target.denies.push(source)
        for (const scope of permission.dataScopes ?? [])
          target.deniedScopes.add(scope)
      }
      else {
        target.allows.push(source)
        for (const scope of permission.dataScopes ?? role?.defaultDataScopes ?? legacyDefaultDataScopes[roleId as LegacyRole] ?? [])
          target.scopes.add(scope)
      }
    }
  }

  for (const override of [...(subject.overrides ?? []), ...(subject.temporaryGrants ?? [])]) {
    if (override.userId !== subject.userId || !activeAt(override.startsAt, override.expiresAt, now))
      continue
    const target = ensure(override.permissionKey)
    const source = 'grantType' in override && override.grantType === 'temporary' ? `临时授权：${override.reason}` : `用户例外：${override.reason}`
    if (override.effect === 'deny')
      target.denies.push(source)
    else
      target.allows.push(source)
  }

  for (const point of permissionCatalog)
    ensure(point.key)

  return [...permissions.entries()].map(([permissionKey, result]) => ({
    permissionKey,
    allowed: result.allows.length > 0 && result.denies.length === 0,
    sources: result.allows,
    deniedBy: result.denies,
    dataScopes: [...result.scopes].filter(scope => !result.deniedScopes.has(scope)),
  }))
}

export function effectivePermission(subject: PermissionSubject, permissionKey: string, now = Date.now()) {
  return computeEffectivePermissions(subject, now).find(item => item.permissionKey === permissionKey) ?? {
    permissionKey,
    allowed: false,
    sources: [],
    deniedBy: [],
    dataScopes: [],
  }
}

export function narrowAiPermissions(effective: EffectivePermission[], allowedKeys?: Iterable<string>) {
  if (!allowedKeys)
    return effective.map(item => ({ ...item, sources: [...item.sources, '被代表用户有效权限'] }))
  const allowed = new Set(allowedKeys)

  return effective.map(item => ({
    ...item,
    allowed: item.allowed && allowed.has(item.permissionKey),
    sources: item.allowed && allowed.has(item.permissionKey) ? [...item.sources, 'AI 收窄规则'] : item.sources,
    deniedBy: item.allowed && !allowed.has(item.permissionKey) ? [...item.deniedBy, 'AI 收窄规则'] : item.deniedBy,
  }))
}

export function roleSubject(role: Role, userId = `demo-${role}`): PermissionSubject {
  // 旧五角色直接进入权限引擎，避免借用某个新模板造成权限放大。
  if (legacyRoles.includes(role as typeof legacyRoles[number]))
    return { userId, roleIds: [role] }

  return { userId, roleIds: [role] }
}

export function canPermission(subject: PermissionSubject, permissionKey: string) {
  return effectivePermission(subject, permissionKey).allowed
}

/** 字段权限在 mock 返回数据前裁剪，页面层不能用视觉隐藏替代。 */
export function fieldAccess(subject: PermissionSubject, fieldKey: string): FieldAccess {
  const fieldPermissionKey = sensitiveFieldPermissionKeys[fieldKey]
  if (fieldPermissionKey && !effectivePermission(subject, fieldPermissionKey).allowed)
    return 'hidden'

  const restrictions: FieldAccess[] = []
  for (const roleId of collectRoleIds(subject.roleIds)) {
    const restriction = templateById.get(roleId)?.fieldRestrictions[fieldKey]
    if (restriction)
      restrictions.push(restriction)
  }
  if (restrictions.includes('hidden'))
    return 'hidden'
  if (restrictions.includes('masked'))
    return 'masked'
  if (restrictions.includes('readonly'))
    return 'readonly'

  return 'visible'
}
