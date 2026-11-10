import { type MaybeRefOrGetter, type Ref, toValue, watch } from 'vue'

import type { ChatState } from './types'

export interface ChatRequestTicket {
  requestId: number
  userId: string | null
}

export interface ChatInflightOptions {
  userId: MaybeRefOrGetter<string | null | undefined>
  isLoggedIn: MaybeRefOrGetter<boolean>
  role: MaybeRefOrGetter<string | null | undefined>
  sending: Ref<boolean>
  state: Ref<ChatState>
  statusText: Ref<string>
}

/**
 * 两个聊天入口共用的在途请求门闩。
 * 写入消息或缓存前必须同时满足请求号、登录态、发起时的 userId；
 * 只相等请求号不够，登出或换用户后旧回调不能写入新会话。
 * 发送/加载状态只按请求号回收，避免旧请求的 finally 清掉新请求的 sending。
 */
export function useChatInflight(options: ChatInflightOptions) {
  let requestId = 0

  function actorId() {
    const actor = toValue(options.userId)

    return toValue(options.isLoggedIn) && actor ? actor : null
  }

  function begin(): ChatRequestTicket {
    requestId += 1

    return {
      requestId,
      userId: actorId(),
    }
  }

  function invalidate() {
    requestId += 1
  }

  function isLatest(ticket: ChatRequestTicket) {
    return ticket.requestId === requestId
  }

  function isCurrent(ticket: ChatRequestTicket) {
    return isLatest(ticket)
      && toValue(options.isLoggedIn) === true
      && ticket.userId !== null
      && ticket.userId === (toValue(options.userId) ?? null)
  }

  function writeIfCurrent(ticket: ChatRequestTicket, write: () => void) {
    if (!isCurrent(ticket))
      return false

    write()

    return true
  }

  function canPersist(hydratedUserId: string | null) {
    const actor = toValue(options.userId) ?? null

    return toValue(options.isLoggedIn) === true && actor !== null && hydratedUserId === actor
  }

  function resetTransport() {
    options.sending.value = false
    options.state.value = 'idle'
    options.statusText.value = ''
  }

  function watchIdentity(reload: () => void) {
    watch(
      [() => toValue(options.isLoggedIn), () => toValue(options.userId), () => toValue(options.role)],
      () => {
        invalidate()
        resetTransport()
        reload()
      },
      { flush: 'sync' },
    )
  }

  return { begin, invalidate, isCurrent, isLatest, writeIfCurrent, canPersist, watchIdentity }
}
