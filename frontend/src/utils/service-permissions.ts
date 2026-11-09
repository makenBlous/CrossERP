import type { Actor } from '@/types/entities'
import { effectivePermission, roleSubject } from '@/utils/permission-engine'

/** Mock 服务层的统一权限断言；页面隐藏按钮不能替代这里的检查。 */
export function requireActorPermission(actor: Actor, permissionKey: string) {
  const result = effectivePermission(roleSubject(actor.role, actor.userId), permissionKey)
  if (!result.allowed)
    throw new Error(`当前用户没有权限：${permissionKey}`)

  return result
}

export function actorCan(actor: Actor, permissionKey: string) {
  return effectivePermission(roleSubject(actor.role, actor.userId), permissionKey).allowed
}

export function assertHumanActor(origin: 'human' | 'ai' = 'human') {
  if (origin === 'ai')
    throw new Error('AI 只能起草，不能直接写入或审批')
}
