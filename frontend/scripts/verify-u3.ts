import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { ref } from 'vue'
import { parseSafeMarkdown } from '../src/components/chat/markdown'
import type { ChatState } from '../src/components/chat/types'
import { useChatHistory } from '../src/components/chat/useChatHistory'
import { useChatInflight } from '../src/components/chat/useChatInflight'

const root = resolve(import.meta.dirname, '..')

const read = (relative: string) => readFileSync(resolve(root, relative), 'utf8')

const assert = (condition: boolean, message: string) => {
  if (!condition)
    throw new Error(`U3 verify failed: ${message}`)
}

for (const file of ['src/components/chat/ChatThread.vue', 'src/views/apps/chat/ChatLog.vue', 'src/views/apps/chat/ChatMessageForm.vue', 'src/components/chat/ChatStatusLine.vue'])
  assert(existsSync(resolve(root, file)), `missing shared chat component ${file}`)

const drawer = read('src/components/biz/AssistantDrawer.vue')
const agent = read('src/pages/agent/chat.vue')
const i18n = read('src/plugins/i18n/ui.ts')

assert(drawer.includes('@/components/chat/ChatThread.vue'), 'assistant drawer must use ChatThread')
assert(agent.includes('@/components/chat/ChatThread.vue'), 'agent center must use ChatThread')
assert(i18n.includes('aiClosed'), 'i18n must define assistant.aiClosed')
assert(i18n.includes('aiClosed: \'AI 已关闭，仍可按人工路径操作；当前不能发送消息。\''), 'zh-CN assistant.aiClosed copy must exist')
assert(i18n.includes('aiClosed: \'AI is off; the manual path remains available, and sending is disabled.\''), 'en assistant.aiClosed copy must exist')
assert(drawer.includes('t(\'assistant.aiClosed\')'), 'assistant drawer must use the translated AI-off message')
assert(agent.includes('t(\'assistant.aiClosed\')'), 'agent center must use the translated AI-off message')
assert(drawer.includes('@retry') && drawer.includes('@cancel'), 'assistant drawer must expose retry and cancel')
assert(agent.includes('@retry') && agent.includes('@cancel'), 'agent center must expose retry and cancel')

const history = read('src/components/chat/useChatHistory.ts')

assert(history.includes('userId'), 'chat history cache key must include stable userId')
assert(history.includes('isLoggedIn'), 'chat history must receive login state')
assert(history.includes('item.local'), 'local cache entries must be explicitly marked local')
assert(history.includes('seedIds'), 'API seed ids must be authoritative over local cache')
assert(history.includes('if (!actor'), 'history must skip cache access when userId is missing')
assert(agent.includes('session.userId'), 'agent center must pass session userId to history')
assert(drawer.includes('session.isLoggedIn') && agent.includes('session.isLoggedIn'), 'logout must clear both chat entries in memory')
assert(drawer.includes('session.role') && agent.includes('session.role'), 'identity or role changes must reload history')
assert(read('src/components/chat/ChatThread.vue').includes('@/views/apps/chat/ChatLog.vue'), 'ChatThread must reuse ChatLog')
assert(read('src/components/chat/ChatThread.vue').includes('@/views/apps/chat/ChatMessageForm.vue'), 'ChatThread must reuse ChatMessageForm')
assert(!read('src/views/apps/chat/ChatLog.vue').includes('v-html'), 'chat markdown must not use v-html')
assert(read('src/views/apps/chat/ChatLog.vue').includes('v-text'), 'chat markdown must render text nodes safely')

const storage = new Map<string, string>()

Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  value: {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  },
})

const actor = ref<string | null>('user-a')
const isLoggedIn = ref(true)
const actorHistory = useChatHistory<{ id: string; text: string; local?: boolean }>('agent-center', actor, isLoggedIn)

assert(actorHistory.cacheKey.value === 'crosserp-chat-history:user-a:agent-center', 'cache key must contain the stable userId')
actorHistory.save([
  { id: 'shared', text: 'user-a cached copy', local: true },
  { id: 'only-a', text: 'user-a only', local: true },
])
actor.value = 'user-b'
assert(actorHistory.load([]).length === 0, 'switching users must not expose the previous user history')
actor.value = 'user-a'

isLoggedIn.value = false
assert(actorHistory.load([]).length === 0, 'logged-out users must not read chat history')
actorHistory.save([{ id: 'blocked', text: 'must not be cached', local: true }])
assert(storage.get('crosserp-chat-history:user-a:agent-center')?.includes('only-a'), 'logout must not delete the previous user cache')
isLoggedIn.value = true
actor.value = 'user-b'
assert(actorHistory.load([]).length === 0, 'a different user after logout must not see the previous user history')
actor.value = 'user-a'

const apiHistory = actorHistory.load([{ id: 'shared', text: 'API authoritative copy', local: false }])

assert(apiHistory.length === 2 && apiHistory[0]?.text === 'API authoritative copy' && apiHistory[1]?.id === 'only-a', 'API history must win over same-ID local cache and retain only local additions')
actor.value = null
isLoggedIn.value = false
actorHistory.save([{ id: 'blocked', text: 'must not be cached', local: true }])
assert(actorHistory.load([]).length === 0, 'missing userId must disable history reads and writes')

const dangerous = parseSafeMarkdown('<script>alert(1)</script>\n<img src=x onerror=alert(1)>')
const renderedText = dangerous.flatMap(block => block.type === 'list' ? block.items : [block.text]).join('\n')

assert(renderedText.includes('<script>alert(1)</script>'), 'script input must remain text')
assert(renderedText.includes('onerror=alert(1)'), 'event handler input must remain text')

function assertCallbackGuard(source: string, label: string) {
  const sendAt = source.indexOf('async function sendMessage')
  const body = source.slice(sendAt)
  const pushAt = body.indexOf('pushPart(')
  const guardAt = body.lastIndexOf('writeIfCurrent(', pushAt)

  assert(source.includes('useChatInflight'), `${label} must use the shared in-flight composable`)
  assert(source.includes('watchIdentity('), `${label} must invalidate in-flight requests on login, user, or role changes`)
  assert(source.includes('canPersist('), `${label} must guard cache writes with the shared session check`)
  assert(!source.includes('let requestId') && !source.includes('currentRequest === requestId'), `${label} must not keep a local request-id-only gate`)
  assert(sendAt >= 0 && pushAt > 0 && guardAt >= 0 && pushAt - guardAt < 120, `${label} must check the shared guard before writing bubbles`)
}

assertCallbackGuard(drawer, 'assistant drawer')
assertCallbackGuard(agent, 'agent center')

const gateLogin = ref(true)
const gateUserId = ref<string | null>('user-a')
const gateRole = ref('admin')
const gateSending = ref(false)
const gateState = ref<ChatState>('idle')
const gateStatus = ref('')

const guardOnly = useChatInflight({
  userId: gateUserId,
  isLoggedIn: gateLogin,
  role: gateRole,
  sending: gateSending,
  state: gateState,
  statusText: gateStatus,
})

const loginTicket = guardOnly.begin()

gateLogin.value = false
assert(!guardOnly.isCurrent(loginTicket), 'logged-out callback must fail the login check even if the request id is unchanged')
let blockedWrites = 0

assert(guardOnly.writeIfCurrent(loginTicket, () => {
  blockedWrites += 1
}) === false && blockedWrites === 0, 'logged-out callback must not write bubbles or cache')
gateLogin.value = true
assert(guardOnly.isCurrent(loginTicket), 'the same logged-in user and request may continue')
gateUserId.value = 'user-b'
assert(!guardOnly.isCurrent(loginTicket), 'user switch must fail the captured userId check even if the request id is unchanged')
assert(guardOnly.writeIfCurrent(loginTicket, () => {
  blockedWrites += 1
}) === false && blockedWrites === 0, 'user switch must not let the old callback write')
gateUserId.value = 'user-a'
assert(guardOnly.isCurrent(loginTicket), 'restoring the captured userId must accept the same request id')
guardOnly.invalidate()
assert(!guardOnly.isCurrent(loginTicket), 'request id mismatch must fail even when the user is unchanged')

const sessionLogin = ref(true)
const sessionUserId = ref<string | null>('user-a')
const sessionRole = ref('admin')
const sessionSending = ref(false)
const sessionState = ref<ChatState>('idle')
const sessionStatus = ref('')
const sessionBubbles: string[] = []
const sessionCache = new Map<string, string>()
let sessionReloads = 0

const sessionGate = useChatInflight({
  userId: sessionUserId,
  isLoggedIn: sessionLogin,
  role: sessionRole,
  sending: sessionSending,
  state: sessionState,
  statusText: sessionStatus,
})

sessionGate.watchIdentity(() => {
  sessionReloads += 1
  sessionBubbles.length = 0
})
sessionSending.value = true
sessionState.value = 'loading'
sessionStatus.value = '正在读取只读数据…'

const staleTicket = sessionGate.begin()

const deliverStale = (text: string) => {
  sessionGate.writeIfCurrent(staleTicket, () => {
    sessionBubbles.push(text)
    if (sessionGate.canPersist(sessionUserId.value))
      sessionCache.set(`crosserp-chat-history:${sessionUserId.value}:assistant`, JSON.stringify(sessionBubbles))
  })
}

deliverStale('user-a reply')
assert(sessionBubbles.includes('user-a reply'), 'current callback may write its own session')
assert(sessionCache.get('crosserp-chat-history:user-a:assistant')?.includes('user-a reply') === true, 'current callback may cache its own session')
sessionLogin.value = false
assert(sessionSending.value === false && sessionState.value === 'idle' && sessionStatus.value === '', 'logout must reset sending and loading')
assert(sessionReloads >= 1 && sessionBubbles.length === 0, 'logout must clear the in-memory session')
deliverStale('after logout')
assert(sessionBubbles.length === 0, 'callback after logout must not write the cleared session')
assert(![...sessionCache.values()].some(value => value.includes('after logout')), 'callback after logout must not write cache')
sessionLogin.value = true
sessionUserId.value = 'user-b'
assert(sessionReloads >= 2, 'switching users must reload history')
deliverStale('leaked into user-b')
assert(sessionBubbles.length === 0, 'in-flight callback must not write the new session after logout and user switch')
assert(sessionCache.get('crosserp-chat-history:user-b:assistant') === undefined, 'in-flight callback must not cache into the new user')
assert(![...sessionCache.values()].some(value => value.includes('leaked into user-b')), 'stale callback must not appear in any chat cache')

const freshTicket = sessionGate.begin()

sessionGate.writeIfCurrent(freshTicket, () => {
  sessionBubbles.push('user-b own')
})
assert(sessionBubbles.includes('user-b own'), 'the new user can write a new request')
deliverStale('still user-a')
assert(!sessionBubbles.includes('still user-a'), 'the old ticket must stay invalid after the new user sends')
sessionSending.value = true
sessionState.value = 'loading'

const roleTicket = sessionGate.begin()

sessionRole.value = 'viewer'
assert(sessionUserId.value === 'user-b', 'role fixture must switch role without changing userId')
assert(!sessionGate.isCurrent(roleTicket), 'role switch must invalidate the in-flight request')
assert(sessionSending.value === false && sessionState.value === 'idle', 'role switch must reset sending and loading')
sessionGate.writeIfCurrent(roleTicket, () => {
  sessionBubbles.push('leaked after role switch')
})
assert(!sessionBubbles.includes('leaked after role switch'), 'role switch must drop the previous in-flight write')

console.log('U3 static checks passed')
