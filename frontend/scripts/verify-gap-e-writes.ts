/* eslint-disable max-statements-per-line, newline-before-return, padding-line-between-statements, antfu/if-newline, @stylistic/ts/brace-style, prefer-template, lines-around-comment */
// 批次 E 独立接口级验收（不是 Codex 写的）：写接口越权 / 作者不能自审 / 重复审核 / 不存在 id / 仅财务空间读隔离
const mem = () => { const m = new Map<string, string>(); return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => { m.set(k, String(v)) }, removeItem: (k: string) => { m.delete(k) }, clear: () => m.clear(), key: (i: number) => [...m.keys()][i] ?? null, get length() { return m.size } } }
;(globalThis as any).sessionStorage = mem(); (globalThis as any).localStorage = mem()
const { createPinia, setActivePinia } = await import('pinia')
setActivePinia(createPinia())
const e: any = await import('@/api/gap-e')
const { currentActor, database } = await import('@/api/mock-client')
const gapEService = await import('@/mocks/services/gap-e')
const { useSessionStore } = await import('@/stores/session')
let fail = 0
const ok = (c: boolean, m: string) => { if (!c) fail++; console.log(`${c ? 'PASS' : 'FAIL'} ${m}`) }
const as = (role: string) => { sessionStorage.setItem('crosserp-auth', '1'); sessionStorage.setItem('crosserp-role', role); const s: any = useSessionStore(); if (typeof s.setRole === 'function') s.setRole(role); else if (typeof s.switchRole === 'function') s.switchRole(role); else s.role = role; if (s.role !== role) throw new Error(`切换角色失败 ${s.role}`) }
const rej = async (f: () => Promise<any>) => { try { const r = await f(); return { ok: r === null || r === undefined, r: JSON.stringify(r)?.slice(0, 50) } } catch (x: any) { return { ok: true, r: String(x?.message ?? x).slice(0, 50) } } }
const file = () => new File(['mock'], 'a.pdf', { type: 'application/pdf' })

const employeeFileDb: any = database().db
gapEService.listEmployeeFiles(employeeFileDb, 'demo-operator', { userId: 'demo-admin', name: '演示管理员', role: 'admin', at: new Date().toISOString() })
employeeFileDb.employeeFiles.unshift({ id: 'verify-custom-operator-file', employeeId: 'operator-alice', name: '本人档案.pdf', kind: 'contract', expiresOn: null, sensitive: true, uploadedAt: new Date().toISOString(), size: '1 KB' })
employeeFileDb.employeeFiles.unshift({ id: 'verify-custom-employee-file', employeeId: 'employee-alice', name: '员工本人档案.pdf', kind: 'contract', expiresOn: null, sensitive: true, uploadedAt: new Date().toISOString(), size: '1 KB' })
ok(gapEService.listEmployeeFiles(employeeFileDb, 'operator-alice', { userId: 'operator-alice', name: '运营 Alice', role: 'operator', at: new Date().toISOString() }).some((item: any) => item.id === 'verify-custom-operator-file'), '非演示运营用户可查看本人档案')
ok(gapEService.listEmployeeFiles(employeeFileDb, 'employee-alice', { userId: 'employee-alice', name: '员工 Alice', role: 'employee', at: new Date().toISOString() }).some((item: any) => item.id === 'verify-custom-employee-file'), '普通员工可查看本人档案')
ok((() => { try { gapEService.listEmployeeFiles(employeeFileDb, 'demo-operator', { userId: 'operator-alice', name: '运营 Alice', role: 'operator', at: new Date().toISOString() }); return false } catch { return true } })(), '运营用户不能查看他人档案')
for (const role of ['finance', 'auditor', 'viewer', 'operator'])
  ok((() => { try { gapEService.listEmployeeFiles(employeeFileDb, 'demo-operator', { userId: `${role}-alice`, name: role, role, at: new Date().toISOString() }); return false } catch { return true } })(), `${role} 不能查看他人档案`)
for (const role of ['admin', 'hr_admin'])
  ok((() => { try { gapEService.listEmployeeFiles(employeeFileDb, 'demo-finance', { userId: `${role}-alice`, name: role, role, at: new Date().toISOString() }); return true } catch { return false } })(), `${role} 可查看任意员工档案`)
ok((() => { try { gapEService.listEmployeeFiles(employeeFileDb, 'demo-operator', { userId: 'external-alice', name: '外部 Alice', role: 'external_viewer', at: new Date().toISOString() }); return false } catch { return true } })(), '无员工范围的身份不能查看档案')
// 1 viewer 写接口全部拒绝
as('viewer')
for (const [n, f] of [
  ['新建文档', () => e.createKbDocument({ title: 't', content: 'c', kind: 'policy', spaceId: 'space-company', tags: [], expiresOn: null })],
  ['空间设为仅财务', () => e.setKbSpaceFinanceOnly('space-company', true)],
  ['新建文件夹', () => e.createKbFolder('space-company', 'x')],
  ['保存成员', () => e.saveKbSpaceMembers('space-company', [], ['viewer'])],
  ['重建索引', () => e.rebuildKbIndex()],
  ['上传附件', () => e.uploadKbAttachment('doc-expense-policy', file())],
  ['新版本', () => e.createKbVersion('doc-expense-policy', 'x')],
  ['上传员工档案文件', () => e.uploadEmployeeFile('emp-001', file(), 'contract')],
] as const) { const r = await rej(f as any); ok(r.ok, `viewer ${n} 被拒（${r.r}）`) }
// 2 仅财务空间读隔离
const vd = await e.fetchKbDocuments('space-finance').catch(() => [])
ok(!JSON.stringify(vd).includes('doc-finance-close'), 'viewer 列不出仅财务空间文档')
const vs = await e.searchKb('结账').catch(() => [])
ok(!JSON.stringify(vs).includes('月末结账前由财务复核'), 'viewer 检索不到仅财务文档正文')
const vf = await rej(() => e.fetchKbDocument('doc-finance-close')); ok(vf.ok, `viewer 直接按 id 读仅财务文档被拒/为空（${vf.r}）`)
// 3 不存在 id
as('admin')
const ne = await rej(() => e.fetchKbDocument('no-such-doc')); ok(ne.ok, `不存在文档返回空或报错，不编造（${ne.r}）`)
const ns = await rej(() => e.submitKbDocument('no-such-doc')); ok(ns.ok, `提交不存在文档被拒（${ns.r}）`)
// 4 作者不能自审；重复审核被拒
as('operator')
let doc: any
try { doc = await e.createKbDocument({ title: '验收文档', content: '内容', kind: 'policy', spaceId: 'space-company', tags: ['验收'], expiresOn: null }); await e.submitKbDocument(doc.id) } catch (x: any) { console.log('INFO operator 不能建文档：' + x?.message); as('finance'); doc = await e.createKbDocument({ title: '验收文档', content: '内容', kind: 'policy', spaceId: 'space-company', tags: ['验收'], expiresOn: null }); await e.submitKbDocument(doc.id) }
const author = (useSessionStore() as any).role
as('admin'); const rv = (await e.fetchKbReviews()).find((r: any) => JSON.stringify(r).includes(doc.id)); as(author)
ok(!!rv, `提交后进入审核队列（${rv?.id}）`)
const selfR = await rej(() => e.decideKbReview(rv.id, 'approve')); ok(selfR.ok, `作者 ${author} 不能审核自己的文档（${selfR.r}）`)
as('admin'); const a1 = await rej(() => e.decideKbReview(rv.id, 'approve')); ok(!a1.ok, `另一人 admin 可以审核（${a1.r}）`)
const a2 = await rej(() => e.decideKbReview(rv.id, 'approve')); ok(a2.ok, `重复审核被拒（${a2.r}）`)
const sub2 = await rej(() => e.submitKbDocument(doc.id)); ok(sub2.ok, `已发布文档不能重复提交（${sub2.r}）`)
// 5 有审核权限的作者（admin）也不能自审
as('admin'); const d2 = await e.createKbDocument({ title: '财务自审验收', content: '内容2', kind: 'sop', spaceId: 'space-company', tags: [], expiresOn: null }); await e.submitKbDocument(d2.id)
const rv2 = (await e.fetchKbReviews()).find((r: any) => JSON.stringify(r).includes(d2.id))
const self2 = await rej(() => e.decideKbReview(rv2.id, 'approve')); ok(self2.ok, `admin 作者（有审核权）不能审核自己提交的文档（按身份 id）（${self2.r}）`)
// 6 批次 E 审计回归：稳定 actorId、附件读回身份、审核原子性、关闭仅财务
as('admin')
const db: any = database().db
const auditStart = db.audit.length
const auditDoc = await e.createKbDocument({ title: 'actorId 回归文档', content: '内容', kind: 'policy', spaceId: 'space-company', tags: [], expiresOn: null })
const createAudit = db.audit.slice(auditStart).find((item: any) => item.action === 'kb.document.created' && item.refId === auditDoc.id)
ok(createAudit?.actorId === currentActor().id, `写审计持久化稳定 actorId（${createAudit?.actorId ?? '缺失'}）`)

as('operator')
const attachmentAuditStart = db.audit.length
await e.uploadKbAttachment('doc-cert-demo', file())
const attachmentViews = db.audit.slice(attachmentAuditStart).filter((item: any) => item.action === 'kb.document.viewed')
ok(attachmentViews.length > 0 && attachmentViews.every((item: any) => item.actorRole === 'operator' && item.actorId === currentActor().id), '附件读回沿用原始身份，不伪装成管理员查看')

as('admin')
const invalidReview = { id: 'regression-review-missing-document', type: 'document', targetId: 'regression-missing-document', title: '无效目标', summary: '', submittedBy: 'demo-operator', submittedByName: '演示运营', submittedAt: new Date().toISOString(), status: 'pending' }
db.kbReviews.unshift(invalidReview)
const invalidDecision = await rej(() => e.decideKbReview(invalidReview.id, 'approve'))
const unchangedReview = db.kbReviews.find((item: any) => item.id === invalidReview.id)
ok(invalidDecision.ok && unchangedReview?.status === 'pending', '审核目标校验失败时审核记录保持 pending（原子更新）')
db.kbReviews = db.kbReviews.filter((item: any) => item.id !== invalidReview.id)

const financeSpaceBefore = await e.fetchKbSpace('space-finance')
await e.saveKbSpaceMembers('space-finance', financeSpaceBefore?.members ?? [], ['finance'])
await e.setKbSpaceFinanceOnly('space-finance', false)
as('operator')
const reopenedFinanceSpace = await e.fetchKbSpace('space-finance')
const reopenedFinanceDocs = await e.fetchKbDocuments('space-finance')
ok(Boolean(reopenedFinanceSpace) && !reopenedFinanceSpace.visibleRoles?.length && reopenedFinanceDocs.some((item: any) => item.id === 'doc-finance-close'), '关闭仅财务后清除 visibleRoles 并恢复非财务可见')
as('admin')
await e.saveKbSpaceMembers('space-finance', financeSpaceBefore?.members ?? [], financeSpaceBefore?.visibleRoles)
await e.setKbSpaceFinanceOnly('space-finance', financeSpaceBefore?.financeOnly ?? true)

const { readFileSync } = await import('node:fs')
const { canRoleOpen, findPageByPath } = await import('@/config/pages')
const { effectivePermission, roleSubject } = await import('@/utils/permission-engine')
const { createVoucherFromIssue, submitVoucher } = await import('@/mocks/services/finance')
const onboardingPage = findPageByPath('/onboarding')
const purchasePage = findPageByPath('/procurement/orders/new')
ok(Boolean(onboardingPage) && canRoleOpen('purchaser', onboardingPage!), '采购可打开自己的上手清单')
ok(Boolean(purchasePage) && canRoleOpen('purchaser', purchasePage!), '采购可打开新建采购单')
ok(!effectivePermission(roleSubject('purchaser', 'demo-purchaser'), 'document:read').allowed, '采购仍无 document:read')
const expiryNotes = gapEService.listNotifications(db, { userId: 'demo-admin', name: '演示管理员', role: 'admin', at: new Date().toISOString() })
ok(expiryNotes.some((item: any) => String(item.title).includes('文档即将到期')), '到期提醒写入收件箱数据源')
ok(readFileSync('src/pages/notifications/index.vue', 'utf8').includes('fetchInboxNotifications'), '消息中心复用收件箱数据源')
ok(readFileSync('src/pages/notifications/inbox.vue', 'utf8').includes('fetchInboxNotifications'), '收件箱入口仍在')
ok(readFileSync('src/pages/hr/employees.vue', 'utf8').includes('RouterView') && readFileSync('src/pages/hr/employees/index.vue', 'utf8').includes('HR02'), '员工列表父路由只作出口')
ok(readFileSync('src/pages/hr/employees/[id].vue', 'utf8').includes('RouterView') && readFileSync('src/pages/hr/employees/[id]/index.vue', 'utf8').includes('HR03'), '员工详情父路由只作出口')
ok(readFileSync('src/pages/finance/vouchers/[id].vue', 'utf8').includes('fetchVoucherDetail'), '异常凭证草稿回退到财务凭证详情')
const operatorActor = { userId: 'demo-operator', name: '演示运营', role: 'operator' as const, at: new Date().toISOString() }
const drafted = createVoucherFromIssue(db, 'iss-1', operatorActor)
const submitted = drafted ? submitVoucher(db, drafted.id, operatorActor) : null
ok(Boolean(drafted?.id) && String(submitted?.id).startsWith('apr-'), `异常凭证提交生成 apr 审批（${submitted?.id ?? '无'}）`)
console.log(`== FAIL ${fail}`)
process.exit(fail ? 1 : 0)
