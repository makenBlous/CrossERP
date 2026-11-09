import { legacyRoleMap, permissionCatalog, roleTemplates } from '@/config/permissions'
import type { Role } from '@/types/domain'
import type { DataScopeRuleType, EffectivePermission, PermissionSubject, RolePermission } from '@/types/foundation'

const templateById = new Map(roleTemplates.map(item => [item.id, item]))

function activeAt(startsAt?: string, expiresAt?: string, now = Date.now()) {
  if (startsAt && Date.parse(startsAt) > now)
    return false
  if (expiresAt && Date.parse(expiresAt) <= now)
    return false

  return true
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
  return permission.source ?? `角色 ${templateById.get(roleId)?.nameZh ?? roleId}`
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
    if (!role)
      continue
    for (const permission of role.permissions) {
      const target = ensure(permission.permissionKey)
      const source = normalizePermissionSource(permission, roleId)
      if (permission.effect === 'deny') {
        target.denies.push(source)
        for (const scope of permission.dataScopes ?? [])
          target.deniedScopes.add(scope)
      }
      else {
        target.allows.push(source)
        for (const scope of permission.dataScopes ?? role.defaultDataScopes)
          target.scopes.add(scope)
      }
    }
  }

  for (const override of [...(subject.overrides ?? []), ...(subject.temporaryGrants ?? [])]) {
    if (override.userId !== subject.userId || !activeAt(override.startsAt, override.expiresAt, now))
      continue
    const target = ensure(override.permissionKey)
    const source = override.grantType === 'temporary' ? `临时授权：${override.reason}` : `用户例外：${override.reason}`
    if (override.effect === 'deny')
      target.denies.push(source)
    else
      target.allows.push(source)
  }

  for (const point of permissionCatalog) {
    ensure(point.key)
  }

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
  const mapped = legacyRoleMap[role] ?? role
  const template = roleTemplates.find(item => item.legacyRole === mapped) ?? roleTemplates.find(item => item.id === role)

  return { userId, roleIds: [template?.id ?? role] }
}

export function canPermission(subject: PermissionSubject, permissionKey: string) {
  return effectivePermission(subject, permissionKey).allowed
}

