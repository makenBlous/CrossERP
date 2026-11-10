import { projectApprovals, projectDashboard } from '@/mocks/project'
import type { DashboardPayload, TodoRow } from '@/types/domain'
import type { ApprovalEntity, MockDatabase } from '@/types/entities'
import type { PermissionSubject } from '@/types/foundation'
import { demoIdentities } from '@/stores/session'
import { effectivePermission } from '@/utils/permission-engine'
import { scopeAllows } from '@/mocks/services/gap-c'

const legacySubmitterIds: Record<string, string> = {
  林夏: 'demo-operator',
  周衡: 'demo-finance',
  对账解释员: 'demo-operator',
}

const departments: Record<string, string> = {
  'demo-operator': '运营部',
  'demo-employee': '运营部',
  'demo-ops-manager': '运营部',
  'demo-department-manager': '运营部',
  'demo-finance': '财务部',
  'demo-purchaser': '供应链部',
}

function submitterId(name: string) {
  if (legacySubmitterIds[name])
    return legacySubmitterIds[name]

  return Object.values(demoIdentities).find(item => item.name === name)?.id
}

export function stableSubmitterId(name: string | undefined) {
  const mapped = name ? submitterId(name) : undefined
  if (mapped)
    return mapped
  const trimmed = name?.trim()

  return trimmed ? `submitter:${trimmed}` : 'submitter:unknown'
}

function approvalStoreAllowed(db: MockDatabase, subject: PermissionSubject, permissionKey: string, approval: ApprovalEntity, ownerId?: string) {
  if (!approval.storeId || !db.stores.some(store => store.id === approval.storeId))
    return false

  return scopeAllows(subject, permissionKey, ownerId, ownerId ? departments[ownerId] : undefined, approval.storeId)
}

export function approvalVisibleToSubject(db: MockDatabase, subject: PermissionSubject, approval: ApprovalEntity, userId: string, displayName: string) {
  if (approval.status !== 'pending')
    return false

  const ownerId = submitterId(approval.submitter)
  const own = approval.submitter === displayName || ownerId === userId
  if (own)
    return true
  if (!ownerId)
    return false

  return effectivePermission(subject, 'approval:approve').allowed
    && approvalStoreAllowed(db, subject, 'approval:approve', approval, ownerId)
}

export function projectMyApprovals(db: MockDatabase, subject: PermissionSubject, userId: string, displayName: string) {
  if (!effectivePermission(subject, 'approval:read').allowed)
    return []

  const projected = projectApprovals(db)

  return projected.filter(item => {
    const source = db.approvals.find(approval => approval.id === item.id)

    return source ? approvalVisibleToSubject(db, subject, source, userId, displayName) : false
  })
}

function todoForPurchaseOrder(id: string, no: string, createdAt: string): TodoRow {
  return {
    id: `po-${id}`,
    kind: 'approval',
    title: no,
    detail: '待审批采购单',
    at: createdAt.slice(0, 10),
    to: `/procurement/orders/${id}`,
  }
}

function todoForApproval(approval: ApprovalEntity): TodoRow {
  return {
    id: `ap-${approval.id}`,
    kind: 'approval',
    title: approval.title,
    detail: approval.summary,
    at: approval.submittedAt.slice(0, 10),
    to: '/approvals',
  }
}

export function projectMyTodos(db: MockDatabase, subject: PermissionSubject, userId: string, displayName: string) {
  const rows: TodoRow[] = []

  if (effectivePermission(subject, 'purchase_order:read').allowed) {
    for (const order of db.purchaseOrders.filter(item => item.status === 'submitted' && (item.submittedById === userId || item.createdBy === displayName)))
      rows.push(todoForPurchaseOrder(order.id, order.no, order.createdAt))
  }

  if (effectivePermission(subject, 'approval:read').allowed) {
    for (const approval of db.approvals.filter(item => approvalVisibleToSubject(db, subject, item, userId, displayName)))
      rows.push(todoForApproval(approval))
  }

  return rows
}

export function projectMyDashboard(db: MockDatabase, subject: PermissionSubject, storeId = 'all', period = '2026-10'): DashboardPayload | undefined {
  if (!effectivePermission(subject, 'report:read').allowed)
    return undefined

  const allowedStoreIds = new Set(db.stores
    .filter(store => scopeAllows(subject, 'report:read', undefined, undefined, store.id))
    .map(store => store.id))

  const selectedStoreIds = storeId === 'all'
    ? allowedStoreIds
    : allowedStoreIds.has(storeId)
      ? new Set([storeId])
      : new Set<string>()

  const scopedOrderIds = new Set(db.orders.filter(order => selectedStoreIds.has(order.storeId)).map(order => order.id))
  const fullStoreAccess = selectedStoreIds.size === db.stores.length

  const scopedDb: MockDatabase = {
    ...db,
    stores: db.stores.filter(store => selectedStoreIds.has(store.id)),
    orders: db.orders.filter(order => selectedStoreIds.has(order.storeId)),
    orderLines: db.orderLines.filter(line => scopedOrderIds.has(line.orderId)),
    profitSnapshots: db.profitSnapshots.filter(row => selectedStoreIds.has(row.storeId)),
    issues: db.issues.filter(issue => selectedStoreIds.has(issue.storeId)),
    reconRuns: db.reconRuns.filter(run => selectedStoreIds.has(run.storeId)),
    approvals: db.approvals.filter(approval => fullStoreAccess
      ? true
      : approval.storeId !== null && selectedStoreIds.has(approval.storeId)),
  }

  return projectDashboard(scopedDb, 'all', period)
}

export { submitterId }
