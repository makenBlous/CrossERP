/**
 * 静态原型的数据出口。
 * 页面只调用 src/api 下的函数。以后把函数体换成请求 /api/v1，返回类型保持不变。
 */
import { toRaw } from 'vue'
import { FlowError } from '@/mocks/services/errors'
import { useMockDbStore } from '@/stores/mockdb'
import { useSessionStore } from '@/stores/session'
import type { Actor } from '@/types/entities'
import { type AppAction, can } from '@/utils/permission'

export function delay(ms = 160) {
  return new Promise<void>(resolve => {
    setTimeout(resolve, ms)
  })
}

export function readMock<T>(data: T): Promise<T> {
  return delay().then(() => cloneMock(data))
}

// 服务层可能返回包含 Pinia 响应式代理的对象，structuredClone 无法复制代理，回退为 JSON 深拷贝（mock 数据本身按 JSON 持久化）。
function cloneMock<T>(data: T): T {
  try {
    return structuredClone(toRaw(data))
  }
  catch {
    return data === undefined ? data : JSON.parse(JSON.stringify(toRaw(data))) as T
  }
}

export function currentActor(): Actor {
  const session = useSessionStore()

  return {
    name: session.displayName,
    role: session.role,
    at: new Date().toISOString(),
  }
}

export function assertCan(action: AppAction) {
  const actor = currentActor()

  if (!can(actor.role, action))
    throw new FlowError('当前角色不能执行这个操作')

  return actor
}

export function database() {
  return useMockDbStore()
}
