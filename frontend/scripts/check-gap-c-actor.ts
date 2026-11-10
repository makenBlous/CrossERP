import { strict as assert } from 'node:assert'
import { readFileSync } from 'node:fs'
import { createPinia, setActivePinia } from 'pinia'
import { useMockDbStore } from '@/stores/mockdb'
import { useSessionStore } from '@/stores/session'
import { listGapCAudit, listGapCPermissionChanges, listGapCUsers, saveGapCMatrix } from '@/mocks/services/gap-c'
import { verifyChain } from '@/mocks/services/audit-module'
import { effectivePermission, roleSubject } from '@/utils/permission-engine'

setActivePinia(createPinia())

const notificationsPage = readFileSync('src/pages/notifications.vue', 'utf8')
const auditListPage = readFileSync('src/views/audit/AuditListPage.vue', 'utf8')
const gapCPage = readFileSync('src/views/gap-c/GapCPage.vue', 'utf8')

assert.match(notificationsPage, /<RouterView\s*\/>/, '通知父路由必须渲染子路由出口')
assert.doesNotMatch(notificationsPage, /fetchInboxNotifications/, '通知父路由不得吞掉 N01/N02')

const inboxPage = readFileSync('src/pages/notifications/inbox.vue', 'utf8')

assert.match(inboxPage, /fetchInboxNotifications/, '收件箱子路由必须调用 fetchInboxNotifications')
assert.match(readFileSync('src/config/pages.ts', 'utf8'), /id: 'N03', path: '\/notifications\/inbox'/, '收件箱必须登记为独立路由')
assert.match(auditListPage, /AuditActorId/, '审计列表必须复用推断操作者组件')
assert.match(gapCPage, /AuditActorId/, 'Gap C 必须复用推断操作者组件')

const session = useSessionStore()
const database = useMockDbStore()

session.setRole('admin')

const beforeAuditCount = database.db.audit.length

saveGapCMatrix([{ roleId: 'store_operator', permissionKey: 'sales_order:read', effect: 'allow', sensitive: false }])

assert.equal(database.db.audit.length, beforeAuditCount + 1)
assert.equal(database.db.audit.at(-1)?.actorId, session.userId)

const users = listGapCUsers()
const sameNameUsers = users.filter(user => user.displayName === '演示管理员')

assert.ok(sameNameUsers.length >= 2)

const matrix = [{ roleId: 'store_operator', permissionKey: 'payment_entry:write', effect: 'allow', sensitive: true }] as const

session.setRole('admin')

assert.equal(sameNameUsers.some(user => user.userId === session.userId), true)

const secondaryAdminId = sameNameUsers.find(user => user.userId !== session.userId)!.userId

assert.doesNotThrow(() => saveGapCMatrix([...matrix], secondaryAdminId))
assert.equal(database.db.audit.at(-1)?.actorId, session.userId)
assert.equal(database.db.audit.at(-1)?.confirmerId, secondaryAdminId)
assert.equal(listGapCPermissionChanges()[0]?.actorId, session.userId)
assert.equal(listGapCPermissionChanges()[0]?.confirmerId, secondaryAdminId)
assert.throws(() => saveGapCMatrix([...matrix], session.userId))

const snapshot = JSON.stringify(matrix)
for (const userId of ['missing-user', 'demo-disabled-admin', 'demo-employee']) {
  assert.throws(() => saveGapCMatrix([...matrix], userId))

  assert.equal(JSON.stringify(matrix), snapshot)
}
assert.equal(effectivePermission(roleSubject('employee', 'demo-employee'), 'permission:write').allowed, false)

const oldEvent = database.db.audit[0]

assert.ok(oldEvent)

delete (oldEvent as Partial<typeof oldEvent>).actorId

const oldRows = listGapCAudit()
const oldRow = oldRows.find(row => row.id === oldEvent.id)

assert.ok(oldRow)
assert.equal(oldRow?.actorIdInferred, true)
assert.match(oldRow?.actorId ?? '', /^role:/)
assert.equal(verifyChain(database.db).ok, true)

console.log('gap-c actor checks passed')
