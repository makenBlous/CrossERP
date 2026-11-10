import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')

const read = (relative: string) => readFileSync(resolve(root, relative), 'utf8')

const assert = (condition: boolean, message: string) => {
  if (!condition)
    throw new Error(`U3 verify failed: ${message}`)
}

for (const file of ['src/components/chat/ChatThread.vue', 'src/components/chat/ChatMessage.vue', 'src/components/chat/ChatComposer.vue', 'src/components/chat/ChatStatusLine.vue'])
  assert(existsSync(resolve(root, file)), `missing shared chat component ${file}`)

const drawer = read('src/components/biz/AssistantDrawer.vue')
const agent = read('src/pages/agent/chat.vue')

assert(drawer.includes('@/components/chat/ChatThread.vue'), 'assistant drawer must use ChatThread')
assert(agent.includes('@/components/chat/ChatThread.vue'), 'agent center must use ChatThread')
assert(drawer.includes('AI 已关闭') || drawer.includes('aiClosed'), 'assistant drawer needs manual fallback when AI is off')
assert(agent.includes('AI 已关闭') || agent.includes('aiClosed'), 'agent center needs manual fallback when AI is off')
assert(drawer.includes('@retry') && drawer.includes('@cancel'), 'assistant drawer must expose retry and cancel')
assert(agent.includes('@retry') && agent.includes('@cancel'), 'agent center must expose retry and cancel')
assert(read('src/components/chat/useChatHistory.ts').includes('localStorage'), 'chat history cache must survive refresh')

console.log('U3 static checks passed')
