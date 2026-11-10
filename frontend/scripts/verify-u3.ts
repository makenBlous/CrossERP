import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { ref } from 'vue'
import { parseSafeMarkdown } from '../src/components/chat/markdown'
import { useChatHistory } from '../src/components/chat/useChatHistory'

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

console.log('U3 static checks passed')
