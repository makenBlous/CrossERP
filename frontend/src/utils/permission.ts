import type { Role } from '@/types/domain'

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

const grants: Record<Role, readonly AppAction[]> = {
  admin: ['view', 'create', 'update', 'delete', 'approve', 'export', 'ship', 'receive', 'suggest'],
  operator: ['view', 'create', 'update', 'export', 'ship', 'receive', 'suggest'],
  finance: ['view', 'approve', 'export', 'suggest'],
  viewer: ['view'],
  auditor: ['view', 'export'],
}

export function can(role: Role, action: AppAction): boolean {
  return grants[role].includes(action)
}
