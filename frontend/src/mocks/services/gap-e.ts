/* eslint-disable max-statements-per-line, no-mixed-operators, sonarjs/no-same-line-conditional */
import type { Actor, MockDatabase } from '@/types/entities'
import type { EmployeeFile, KbAccessLog, KbDocument, KbExpiryItem, KbQaItem, KbReviewItem, KbSearchResult, KbSpace, OnboardingAnswer, OnboardingChecklistItem } from '@/types/gap-e'
import { nextId } from '@/mocks/services/ids'
import { writeAudit } from '@/mocks/services/audit'

interface GapCollections {
  kbSpaces: KbSpace[]
  kbDocuments: KbDocument[]
  kbReviews: KbReviewItem[]
  kbQa: KbQaItem[]
  kbAccessLogs: KbAccessLog[]
  employeeFiles: EmployeeFile[]
  onboardingItems: OnboardingChecklistItem[]
  kbIndexVersion: number
}

function collections(db: MockDatabase): GapCollections {
  const value = db as MockDatabase & Partial<GapCollections>

  value.kbSpaces ??= [{ id: 'space-company', name: '公司制度', description: '报销、采购与日常操作制度', memberCount: 18, financeOnly: false, updatedAt: '2026-11-10T08:00:00Z' }, { id: 'space-finance', name: '财务制度', description: '仅财务可见的账务制度和结算说明', memberCount: 4, financeOnly: true, updatedAt: '2026-11-09T08:00:00Z' }]
  value.kbDocuments ??= [{ id: 'doc-expense-policy', spaceId: 'space-company', title: '费用报销制度', content: '员工提交报销时，需要提供发票、付款凭证和审批单。每笔费用应填写发生日期、用途和归属部门。', kind: 'policy', status: 'published', tags: ['报销', '制度'], sensitive: false, expiresOn: null, owner: '人事行政', currentVersion: 1, versions: [{ id: 'ver-expense-1', docId: 'doc-expense-policy', version: 1, content: '员工提交报销时，需要提供发票、付款凭证和审批单。每笔费用应填写发生日期、用途和归属部门。', author: '人事行政', createdAt: '2026-11-01T08:00:00Z', status: 'published' }], updatedAt: '2026-11-01T08:00:00Z' }, { id: 'doc-finance-close', spaceId: 'space-finance', title: '月末结账操作手册', content: '月末结账前由财务复核对账异常、凭证借贷平衡和未完成审批。', kind: 'sop', status: 'published', tags: ['结账', '财务'], sensitive: true, expiresOn: null, owner: '财务部', currentVersion: 1, versions: [{ id: 'ver-finance-1', docId: 'doc-finance-close', version: 1, content: '月末结账前由财务复核对账异常、凭证借贷平衡和未完成审批。', author: '财务部', createdAt: '2026-11-01T08:00:00Z', status: 'published' }], updatedAt: '2026-11-01T08:00:00Z' }, { id: 'doc-cert-demo', spaceId: 'space-company', title: '商品合规证书', content: '商品合规证书原件由人事行政统一保管。', kind: 'certificate', status: 'published', tags: ['证书'], sensitive: true, expiresOn: '2026-11-30', owner: '人事行政', currentVersion: 1, versions: [{ id: 'ver-cert-1', docId: 'doc-cert-demo', version: 1, content: '商品合规证书原件由人事行政统一保管。', author: '人事行政', createdAt: '2026-10-30T08:00:00Z', status: 'published' }], updatedAt: '2026-10-30T08:00:00Z' }]
  value.kbReviews ??= []
  value.kbQa ??= []
  value.kbAccessLogs ??= []
  value.employeeFiles ??= [{ id: 'file-employee-contract', employeeId: 'demo-operator', name: '劳动合同.pdf', kind: 'contract', expiresOn: null, sensitive: true, uploadedAt: '2026-10-01T08:00:00Z', size: '248 KB' }, { id: 'file-employee-cert', employeeId: 'demo-operator', name: '资格证书.pdf', kind: 'certificate', expiresOn: '2026-11-30', sensitive: true, uploadedAt: '2026-10-01T08:00:00Z', size: '128 KB' }]
  value.onboardingItems ??= [{ id: 'onboard-1', roleId: 'purchaser', title: '查看采购制度', description: '了解供应商询价和采购单提交规则', route: '/kb/docs/doc-expense-policy', done: false }, { id: 'onboard-2', roleId: 'purchaser', title: '创建第一张采购单', description: '从采购单页面开始一次完整演练', route: '/procurement/orders/new', done: false }, { id: 'onboard-3', roleId: 'operator', title: '查看运营工作台', description: '熟悉订单、库存与异常入口', route: '/dashboard', done: true }, { id: 'onboard-4', roleId: 'operator', title: '了解报销制度', description: '确认提交报销所需的票据', route: '/kb/docs/doc-expense-policy', done: false }]
  value.kbIndexVersion ??= 1

  return value as MockDatabase & GapCollections
}

function canReadSpace(space: KbSpace, actor: Actor) {
  return !space.financeOnly || actor.role === 'admin' || actor.role === 'finance'
}

export function listSpaces(db: MockDatabase, actor: Actor) { return collections(db).kbSpaces.filter(space => canReadSpace(space, actor)) }
export function getSpace(db: MockDatabase, id: string, actor: Actor) {
  const space = collections(db).kbSpaces.find(item => item.id === id)

  return space && canReadSpace(space, actor) ? space : null
}
export function listDocuments(db: MockDatabase, actor: Actor, spaceId?: string) {
  const c = collections(db)

  return c.kbDocuments.filter(doc => (!spaceId || doc.spaceId === spaceId) && doc.status !== 'archived' && canReadSpace(c.kbSpaces.find(space => space.id === doc.spaceId)!, actor))
}
export function getDocument(db: MockDatabase, id: string, actor: Actor) {
  const doc = collections(db).kbDocuments.find(item => item.id === id)

  return doc && canReadSpace(collections(db).kbSpaces.find(space => space.id === doc.spaceId)!, actor) ? doc : null
}
export function search(db: MockDatabase, query: string, actor: Actor): KbSearchResult[] {
  const q = query.trim().toLowerCase()

  return listDocuments(db, actor).filter(doc => `${doc.title} ${doc.content} ${doc.tags.join(' ')}`.toLowerCase().includes(q)).map(doc => ({ id: `${doc.id}-${doc.currentVersion}`, title: doc.title, excerpt: doc.content.slice(0, 120), spaceName: collections(db).kbSpaces.find(space => space.id === doc.spaceId)?.name ?? '', docId: doc.id, version: doc.currentVersion, paragraph: doc.content }))
}
export function createDocument(db: MockDatabase, input: Pick<KbDocument, 'title' | 'content' | 'kind' | 'spaceId' | 'tags' | 'expiresOn'>, actor: Actor) {
  const doc: KbDocument = { id: nextId(db, 'kbdoc'), ...input, status: 'draft', sensitive: false, owner: actor.name, currentVersion: 1, versions: [{ id: nextId(db, 'kbver'), docId: 'pending', version: 1, content: input.content, author: actor.name, createdAt: actor.at, status: 'draft' }], updatedAt: actor.at }

  doc.versions[0].docId = doc.id; collections(db).kbDocuments.unshift(doc); writeAudit(db, actor, 'kb.document.created', 'kb_doc', doc.id, `创建知识文档 ${doc.title}`)

  return doc
}
export function submitDocument(db: MockDatabase, id: string, actor: Actor) {
  const doc = getDocument(db, id, actor); if (!doc)
    throw new Error('无权提交或文档不存在'); doc.status = 'in_review'; doc.versions[doc.versions.length - 1].status = 'in_review'; collections(db).kbReviews.unshift({ id: nextId(db, 'kbr'), type: 'document', targetId: id, title: doc.title, summary: doc.content.slice(0, 90), submittedBy: actor.name, submittedAt: actor.at, status: 'pending' }); writeAudit(db, actor, 'kb.document.submitted', 'kb_doc', id, '提交文档审核')

  return doc
}
export function addVersion(db: MockDatabase, id: string, content: string, actor: Actor) {
  const doc = getDocument(db, id, actor); if (!doc)
    throw new Error('无权编辑或文档不存在'); const version = doc.currentVersion + 1

  doc.currentVersion = version; doc.content = content; doc.status = 'draft'; doc.updatedAt = actor.at; doc.versions.push({ id: nextId(db, 'kbver'), docId: id, version, content, author: actor.name, createdAt: actor.at, status: 'draft' }); writeAudit(db, actor, 'kb.document.version_created', 'kb_doc', id, `创建第 ${version} 版`)

  return doc
}
export function listReviews(db: MockDatabase, actor: Actor) {
  if (!['admin', 'finance'].includes(actor.role))
    return []

  return collections(db).kbReviews.filter(item => item.status === 'pending')
}
export function decideReview(db: MockDatabase, id: string, decision: 'approve' | 'reject', reason: string, actor: Actor) {
  const review = collections(db).kbReviews.find(item => item.id === id); if (!review || !['admin', 'finance'].includes(actor.role))
    throw new Error('当前角色不能处理审核'); review.status = decision === 'approve' ? 'approved' : 'rejected'; review.reason = reason; if (review.type === 'document') { const doc = collections(db).kbDocuments.find(item => item.id === review.targetId); if (doc) { doc.status = decision === 'approve' ? 'published' : 'draft'; doc.versions[doc.versions.length - 1].status = doc.status } }
  else {
    const qa = collections(db).kbQa.find(item => item.id === review.targetId); if (qa)
      qa.status = decision === 'approve' ? 'published' : 'pending'
  } writeAudit(db, actor, `kb.review.${decision}`, 'kb_review', id, decision === 'approve' ? '批准并发布' : `驳回：${reason || '未填写原因'}`)

  return review
}
export function suggestQa(db: MockDatabase, ticketId: string, actor: Actor) {
  const doc = collections(db).kbDocuments.find(item => item.id === 'doc-expense-policy')!; const qa: KbQaItem = { id: nextId(db, 'kbqa'), question: '报销需要哪些票据？', answer: '请提供发票、付款凭证和审批单，并填写发生日期、用途和归属部门。', citationDocId: doc.id, citationVersion: doc.currentVersion, citationLabel: `${doc.title} v${doc.currentVersion}`, status: 'pending', sourceRef: ticketId, tags: ['报销', '工单经验'] }

  collections(db).kbQa.unshift(qa); collections(db).kbReviews.unshift({ id: nextId(db, 'kbr'), type: 'qa', targetId: qa.id, title: qa.question, summary: `来自已解决工单 ${ticketId}`, submittedBy: actor.name, submittedAt: actor.at, status: 'pending' }); writeAudit(db, actor, 'kb.qa.suggested', 'kb_qa', qa.id, `从工单 ${ticketId} 生成建议问答`)

  return qa
}
export function listQa(db: MockDatabase, actor: Actor) { return collections(db).kbQa.filter(item => item.status === 'published' && canReadSpace(collections(db).kbSpaces.find(space => space.id === 'space-company')!, actor)) }
export function listExpiring(db: MockDatabase, actor: Actor): KbExpiryItem[] {
  if (!['admin', 'finance'].includes(actor.role))
    return []

  return collections(db).kbDocuments.filter(doc => doc.expiresOn).map(doc => ({ id: doc.id, docId: doc.id, title: doc.title, kind: doc.kind, expiresOn: doc.expiresOn!, daysRemaining: Math.max(0, Math.ceil((new Date(doc.expiresOn!).getTime() - Date.now()) / 86400000)), owner: doc.owner, status: new Date(doc.expiresOn!).getTime() < Date.now() ? 'expired' : 'upcoming' }))
}
export function rebuildIndex(db: MockDatabase, actor: Actor) {
  if (actor.role !== 'admin')
    throw new Error('只有管理员可以重建索引'); collections(db).kbIndexVersion += 1; writeAudit(db, actor, 'kb.index.rebuilt', 'kb_index', String(collections(db).kbIndexVersion), `重建索引 v${collections(db).kbIndexVersion}`)

  return collections(db).kbIndexVersion
}
export function listAccessLogs(db: MockDatabase, actor: Actor) {
  if (!['admin', 'auditor'].includes(actor.role))
    return []

  return collections(db).kbAccessLogs
}
export function listEmployeeFiles(db: MockDatabase, employeeId: string, actor: Actor) {
  if (!(actor.role === 'admin' || actor.role === 'operator' && actor.name.includes('运营') || actor.role === 'employee'))
    throw new Error('当前身份无权查看员工档案'); if (actor.role === 'operator' && employeeId !== 'demo-operator')
    throw new Error('只能查看本人档案')

  return collections(db).employeeFiles.filter(file => file.employeeId === employeeId)
}
export function downloadEmployeeFile(db: MockDatabase, id: string, employeeId: string, actor: Actor) {
  const file = listEmployeeFiles(db, employeeId, actor).find(item => item.id === id); if (!file)
    throw new Error('文件不存在或无权下载'); collections(db).kbAccessLogs.unshift({ id: nextId(db, 'kba'), docId: file.id, title: file.name, actor: actor.name, actorRole: actor.role, action: 'download', at: actor.at, origin: 'human' }); writeAudit(db, actor, 'kb.personal.downloaded', 'employee_file', id, `下载敏感档案 ${file.name}`)

  return file
}
export function listOnboarding(db: MockDatabase, roleId: string) { return collections(db).onboardingItems.filter(item => item.roleId === roleId || item.roleId === 'operator') }
export function saveOnboardingItem(db: MockDatabase, item: OnboardingChecklistItem, actor: Actor) {
  if (actor.role !== 'admin')
    throw new Error('只有管理员可以维护上手清单'); const rows = collections(db).onboardingItems; const existing = rows.find(row => row.id === item.id); if (existing)
    Object.assign(existing, item); else rows.push({ ...item, id: nextId(db, 'onboard') }); writeAudit(db, actor, 'onboarding.checklist.updated', 'onboarding', item.id, '更新新人上手清单')

  return item
}
export function askKnowledge(db: MockDatabase, query: string, actor: Actor): OnboardingAnswer {
  const hits = search(db, query, actor); const hit = hits[0]; if (!hit)
    return { answer: '当前权限范围内没有找到可引用的制度文档。', citations: [] }; if (query.includes('报销'))
    return { answer: '报销需要发票、付款凭证和审批单，并填写发生日期、用途和归属部门。', citations: [{ label: `${hit.title} v${hit.version} · 段落 1`, href: `/kb/docs/${hit.docId}`, docId: hit.docId, version: hit.version }] }

  return { answer: `根据《${hit.title}》：${hit.paragraph}`, citations: [{ label: `${hit.title} v${hit.version} · 段落 1`, href: `/kb/docs/${hit.docId}`, docId: hit.docId, version: hit.version }] }
}
