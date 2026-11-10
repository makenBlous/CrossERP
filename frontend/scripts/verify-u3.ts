import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'
import { parseSafeMarkdown } from '../src/components/chat/markdown'
import type { ChatState } from '../src/components/chat/types'
import { useChatHistory } from '../src/components/chat/useChatHistory'
import { useChatInflight } from '../src/components/chat/useChatInflight'
import { recordAgentQuestion, recordSuggestionStep, submitAgentSuggestion } from '@/api/agent-module'
import { addSuggestionStep } from '@/mocks/services/agent-module'
import { useMockDbStore } from '@/stores/mockdb'
import { useSessionStore } from '@/stores/session'

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

const agentApi = read('src/api/agent-module.ts')
const suggestionService = read('src/mocks/services/agent-module.ts')

assert(agentApi.includes('会话已变更，已放弃写入'), 'identity change must use the explicit abandon reason')
assert((agentApi.match(/bindInitiator\(/g) ?? []).length >= 4, 'question, suggestion step, and suggestion submit must share bindInitiator')
assert(agent.includes('from \'@/api/agent-module\'') && !agent.includes('@/api/workflows'), 'agent center must submit suggestions through the initiator-bound API')
assert(drawer.includes('from \'@/api/agent-module\'') && !drawer.includes('@/api/workflows'), 'assistant drawer must submit suggestions through the initiator-bound API')
assert(suggestionService.includes('if (!actor.userId)'), 'suggestion step must reject an empty userId before the role fallback')

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

setActivePinia(createPinia())

const persistSession = useSessionStore()
const persistDb = useMockDbStore()
const switchedQuestion = 'ux-chat-cross-user-persist-probe'

persistSession.login('user-a')
persistSession.setRole('admin')
assert(persistSession.isLoggedIn && persistSession.userId === 'demo-admin', 'fixture must start logged in as the initiator')

const beforeRunIds = new Set(persistDb.db.agentRuns.map(run => run.id))
const beforeAuditIds = new Set(persistDb.db.audit.map(event => event.id))
const pendingQuestion = recordAgentQuestion(switchedQuestion)

persistSession.logout()
persistSession.setRole('finance')
persistSession.login('user-b')
assert(persistSession.isLoggedIn && persistSession.userId === 'demo-finance' && persistSession.userId !== 'demo-admin', 'fixture must switch to a different logged-in user before the delayed return')

try {
  await pendingQuestion
}
catch {
  // 身份变化后放弃写入；数据库断言不依赖拒绝或成功返回。
}

const newRuns = persistDb.db.agentRuns.filter(run => !beforeRunIds.has(run.id))
const newAudits = persistDb.db.audit.filter(event => !beforeAuditIds.has(event.id))
const questionRuns = newRuns.filter(run => run.question === switchedQuestion)
const questionAudits = newAudits.filter(event => questionRuns.some(run => run.id === event.refId) || event.summary.includes(switchedQuestion))

assert(questionRuns.length === 0, 'send, logout, switch user, then delayed return must abandon the write')
assert(!questionAudits.some(event => event.actorId === persistSession.userId), 'the question must not be recorded as the new user')
assert(!newAudits.some(event => !event.actorId), 'new records must not omit actorId')
assert(!questionAudits.some(event => !event.actorId), 'the question must not be recorded without actorId')

persistSession.setRole('admin')
persistSession.login('user-a')

const sameQuestion = 'ux-chat-initiator-persist-probe'
const beforeSameAuditIds = new Set(persistDb.db.audit.map(event => event.id))
const sameRun = await recordAgentQuestion(sameQuestion)
const sameAudits = persistDb.db.audit.filter(event => !beforeSameAuditIds.has(event.id) && event.refId === sameRun.id)

assert(sameAudits.length > 0 && sameAudits.every(event => event.actorId === 'demo-admin'), 'a stable session must record the initiator actorId')
assert(persistDb.db.agentRuns.some(run => run.id === sameRun.id && run.question === sameQuestion), 'a stable session must persist the initiator question')

const suggestionMarker = 'ux-chat-suggestion-cross-user-probe'
const stepRunId = 'ux-chat-suggestion-step-cross-user'

const suggestionDraft = {
  title: suggestionMarker,
  summary: suggestionMarker,
  amount: '10.00',
  currency: 'CNY' as const,
  storeId: null,
  targetType: 'issue_note',
  targetId: 'issue-probe',
}

persistSession.setRole('admin')
persistSession.login('user-a')
assert(persistSession.userId === 'demo-admin', 'suggestion fixture must start as the initiator')

const beforeApprovalIds = new Set(persistDb.db.approvals.map(item => item.id))
const beforeStepIds = new Set((persistDb.db.agentRunSteps ?? []).map(item => item.id))
const beforeSuggestionAuditIds = new Set(persistDb.db.audit.map(event => event.id))
const pendingSuggestion = submitAgentSuggestion(suggestionDraft)
const pendingStep = recordSuggestionStep(stepRunId, suggestionMarker)

persistSession.logout()
persistSession.setRole('operator')
persistSession.login('user-b')
assert(persistSession.isLoggedIn && persistSession.userId === 'demo-operator' && persistSession.userId !== 'demo-admin', 'suggestion fixture must switch to a different user who can still write suggestions')

let suggestionError = ''
let stepError = ''

try {
  await pendingSuggestion
}
catch (error) {
  suggestionError = error instanceof Error ? error.message : String(error)
}
try {
  await pendingStep
}
catch (error) {
  stepError = error instanceof Error ? error.message : String(error)
}

const newSteps = (persistDb.db.agentRunSteps ?? []).filter(item => !beforeStepIds.has(item.id))
const newApprovals = persistDb.db.approvals.filter(item => !beforeApprovalIds.has(item.id))
const newSuggestionAudits = persistDb.db.audit.filter(event => !beforeSuggestionAuditIds.has(event.id))
const leakedSteps = newSteps.filter(item => item.runId === stepRunId || item.detail.includes(suggestionMarker))
const leakedApprovals = newApprovals.filter(item => item.title === suggestionMarker || item.summary.includes(suggestionMarker) || item.targetId === 'issue-probe')
const leakedAudits = newSuggestionAudits.filter(event => event.actorId === 'demo-operator' || event.summary.includes(suggestionMarker) || event.refId === suggestionMarker)

assert(suggestionError.includes('会话已变更，已放弃写入'), 'identity change must abandon the suggestion with an explicit reason')
assert(stepError.includes('会话已变更，已放弃写入'), 'identity change must abandon the suggestion step with an explicit reason')
assert(!suggestionError.includes('没有权限') && !stepError.includes('没有权限'), 'abandoning a suggestion must not look like a permission denial')
assert(leakedSteps.length === 0, 'send suggestion, logout, switch user, then delayed return must not write a step for the new user')
assert(leakedApprovals.length === 0, 'send suggestion, logout, switch user, then delayed return must not write an approval for the new user')
assert(leakedAudits.length === 0, 'send suggestion, logout, switch user, then delayed return must not write an audit for the new user')
assert(!newSuggestionAudits.some(event => !event.actorId), 'new suggestion audits must not omit actorId')

persistSession.logout()

let loggedOutError = ''

try {
  await submitAgentSuggestion(suggestionDraft)
}
catch (error) {
  loggedOutError = error instanceof Error ? error.message : String(error)
}
assert(loggedOutError.includes('没有权限：agent_suggestion:create'), 'a logged-out suggestion must stay a permission denial')
assert(!loggedOutError.includes('会话已变更'), 'a permission denial must not use the session-changed reason')

persistSession.setRole('viewer')
persistSession.login('viewer')

let viewerError = ''

try {
  await recordSuggestionStep(stepRunId, suggestionMarker)
}
catch (error) {
  viewerError = error instanceof Error ? error.message : String(error)
}
assert(viewerError.includes('没有权限：agent_tool:write'), 'a viewer must still be denied suggestion steps')
assert(!viewerError.includes('会话已变更'), 'a real permission denial must not use the session-changed reason')

const escalateMarker = 'ux-chat-suggestion-escalate-probe'

persistSession.setRole('operator')
persistSession.login('operator-init')

const pendingEscalate = submitAgentSuggestion({ ...suggestionDraft, title: escalateMarker, summary: escalateMarker, targetId: 'issue-escalate' })

persistSession.logout()
persistSession.setRole('admin')
persistSession.login('admin-later')

let escalateError = ''

try {
  await pendingEscalate
}
catch (error) {
  escalateError = error instanceof Error ? error.message : String(error)
}
assert(escalateError.includes('会话已变更，已放弃写入'), 'switching to a higher role must abandon the original suggestion')
assert(!persistDb.db.approvals.some(item => item.title === escalateMarker || item.targetId === 'issue-escalate'), 'a later admin must not receive the earlier user suggestion')

persistSession.setRole('admin')
persistSession.login('user-a')

const stableMarker = 'ux-chat-suggestion-initiator-probe'
const beforeStableAuditIds = new Set(persistDb.db.audit.map(event => event.id))
const stableApproval = await submitAgentSuggestion({ ...suggestionDraft, title: stableMarker, summary: stableMarker, targetId: 'issue-stable' })

await recordSuggestionStep(sameRun.id, stableApproval.id)

const stableAudits = persistDb.db.audit.filter(event => !beforeStableAuditIds.has(event.id) && (event.refId === stableApproval.id || event.summary.includes(stableApproval.id)))
const stableSteps = (persistDb.db.agentRunSteps ?? []).filter(item => item.runId === sameRun.id && item.detail.includes(stableApproval.id))

assert(stableApproval.status === 'pending' && stableApproval.submitter === '演示管理员', 'a stable suggestion must stay pending under the initiator')
assert(stableSteps.length === 1, 'a stable session must record the suggestion step')
assert(stableAudits.length > 0 && stableAudits.every(event => event.actorId === 'demo-admin'), 'approval, step, and audit actorId must be the initiator')

let selfApprovalError = ''

try {
  persistDb.decide(stableApproval.id, 'approved', { userId: 'demo-admin', name: '演示管理员', role: 'admin', at: new Date().toISOString() }, '')
}
catch (error) {
  selfApprovalError = error instanceof Error ? error.message : String(error)
}
assert(selfApprovalError.includes('不能审批自己'), 'the initiator must not self-approve the suggestion')
assert(persistDb.db.approvals.find(item => item.id === stableApproval.id)?.status === 'pending', 'a rejected self-approval must leave the suggestion pending')

const beforeEmptySteps = (persistDb.db.agentRunSteps ?? []).length
let emptyActorError = ''

try {
  addSuggestionStep(persistDb.db, 'empty-actor', 'apr-empty', { userId: '', name: '空身份', role: 'admin', at: new Date().toISOString() })
}
catch (error) {
  emptyActorError = error instanceof Error ? error.message : String(error)
}
assert(emptyActorError.includes('没有权限：agent_tool:write'), 'an empty userId must not inherit the role demo identity')
assert((persistDb.db.agentRunSteps ?? []).length === beforeEmptySteps, 'an empty userId must not write a suggestion step')

console.log('U3 static checks passed')
