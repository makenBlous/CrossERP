import type { Role } from '@/types/domain'
import { legacyPermissionKeys } from '@/config/permissions'
import { canPermission, roleSubject } from '@/utils/permission-engine'

export type AppAction =
  | 'view'
  | 'create'
  | 'update'
  | 'delete'
  | 'approve'
  | 'export'
  | 'ship'
  | 'receive'
  | 'suggest'

/** 兼容旧页面的动作名，实际判断统一走权限表有效权限结果。 */
export function can(role: Role, action: AppAction): boolean {
  const key = legacyPermissionKeys[action]

  return key ? canPermission(roleSubject(role), key) : false
}

export function canField(role: Role, fieldKey: string): boolean {
  return canPermission(roleSubject(role), fieldKey)
}

export function canAi(role: Role, permissionKey: string, narrowedKeys?: Iterable<string>): boolean {
  if (!canPermission(roleSubject(role), permissionKey))
    return false
  if (!narrowedKeys)
    return true

  return new Set(narrowedKeys).has(permissionKey)
}
