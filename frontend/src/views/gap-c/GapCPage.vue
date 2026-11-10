<script setup lang="ts">
/* eslint-disable indent, max-statements-per-line */
import { computed, onMounted, ref, watch } from 'vue'
import {
  confirmGapCAccessReview,
  copyGapCRole,
  createGapCReport,
  createGapCTemporaryGrant,
  decideGapCApproval,
  fetchGapCAccessReviews,
  fetchGapCAgentTrace,
  fetchGapCAlerts,
  fetchGapCApprovalRules,
  fetchGapCApprovals,
  fetchGapCArchiveRuns,
  fetchGapCAudit,
  fetchGapCDataScopes,
  fetchGapCEffectivePermissions,
  fetchGapCFieldPolicies,
  fetchGapCMatrix,
  fetchGapCNotifications,
  fetchGapCPermissionChanges,
  fetchGapCReports,
  fetchGapCRetention,
  fetchGapCRole,
  fetchGapCSodRules,
  fetchGapCSubscriptions,
  fetchGapCTemporaryGrants,
  fetchGapCUsers,
  markGapCNotificationRead,
  resolveGapCAlert,
  runGapCArchive,
  runGapCReport,
  saveGapCApprovalRule,
  saveGapCDataScope,
  saveGapCFieldPolicy,
  saveGapCMatrix,
  saveGapCRetention,
  saveGapCSodRule,
  saveGapCSubscriptions,
} from '@/api/gap-c'
import { fetchScopedContext, fetchScopedEmployees, fetchScopedExpenses, fetchScopedOrders } from '@/api/scoped-reads'
import DetailPage from '@/components/biz/DetailPage.vue'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import FormPage from '@/components/biz/FormPage.vue'
import ListPage, { type ListColumn } from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import RecordDrawer from '@/components/biz/RecordDrawer.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import KpiCard from '@/components/KpiCard.vue'
import { findPageById } from '@/config/pages'
import { useAiModeStore } from '@/stores/ai-mode'
import { useSessionStore } from '@/stores/session'
import { useConfirm } from '@/composables/useConfirm'
import type { FieldAccess, GapCAccessReview, GapCAgentTrace, GapCAlert, GapCApprovalRow, GapCApprovalRule, GapCArchiveRun, GapCAuditRow, GapCDataScope, GapCFieldPolicy, GapCMatrixCell, GapCNotification, GapCPermissionChange, GapCReport, GapCReportBuilder, GapCReportResult, GapCRetention, GapCRoleView, GapCSodRule, GapCSubscription, GapCTemporaryGrant } from '@/types/gap-c'

interface RowRecord { id: string; [key: string]: unknown }

const props = defineProps<{ pageId: string }>()
const router = useRouter()
const route = useRoute()
const routeParams = route.params as Record<string, string | string[] | undefined>
const aiMode = useAiModeStore()
const session = useSessionStore()
const page = computed(() => findPageById(props.pageId))
const loading = ref(false)
const error = ref('')
const notice = ref('')
const approvals = ref<GapCApprovalRow[]>([])
const approvalRules = ref<GapCApprovalRule[]>([])
const notifications = ref<GapCNotification[]>([])
const subscriptions = ref<GapCSubscription[]>([])
const reports = ref<GapCReport[]>([])
const reportResult = ref<GapCReportResult | null>(null)
const auditRows = ref<GapCAuditRow[]>([])
const trace = ref<GapCAgentTrace | null>(null)
const alerts = ref<GapCAlert[]>([])
const retention = ref<GapCRetention | null>(null)
const archiveRuns = ref<GapCArchiveRun[]>([])
const fieldPolicies = ref<GapCFieldPolicy[]>([])
const dataScopes = ref<GapCDataScope[]>([])
const temporaryGrants = ref<GapCTemporaryGrant[]>([])
const accessReviews = ref<GapCAccessReview[]>([])
const selectedRole = ref<GapCRoleView | null>(null)
const roleCopyDrawer = ref(false)
const roleCopyName = ref('')
const roleCopyNameEn = ref('')
const roleCopyScope = ref('store')
const roleCopyUsers = ref('demo-operator')
const matrix = ref<GapCMatrixCell[]>([])
const effective = ref<Array<{ permissionKey: string; labelZh: string; allowed: boolean; sources: string[]; deniedBy: string[]; module: string; sensitive: boolean }>>([])
const changes = ref<GapCPermissionChange[]>([])
const sodRules = ref<GapCSodRule[]>([])
const selectedUser = ref('demo-operator')
const period = ref('2026-11')
const reportQuery = ref('')
const confirmerId = ref('')
const gapCUsers = ref<Awaited<ReturnType<typeof fetchGapCUsers>>>([])
const reportName = ref('')
const reportDescription = ref('')
const reportDataSource = ref<GapCReportBuilder['dataSource']>('orders')
const reportFields = ref<string[]>(['orderNo', 'store', 'amount', 'status'])
const reportFilterField = ref('status')
const reportFilterValue = ref('')
const reportResultPreview = ref<GapCReportResult | null>(null)
const grantUser = ref('demo-operator')
const grantPermission = ref('sku.cost:read')
const grantReason = ref('')
const grantExpires = ref('2026-11-17T00:00:00Z')
const grantDrawer = ref(false)
const ruleDrawer = ref(false)
const selectedRecord = ref<RowRecord | null>(null)
const recordDrawer = ref(false)
const selectedRule = ref<GapCApprovalRule | null>(null)
const scopedOrders = ref<Awaited<ReturnType<typeof fetchScopedOrders>>>([])
const scopedExpenses = ref<Awaited<ReturnType<typeof fetchScopedExpenses>>>([])
const scopedEmployees = ref<Awaited<ReturnType<typeof fetchScopedEmployees>>>([])
const scopedContext = ref<Awaited<ReturnType<typeof fetchScopedContext>> | null>(null)
const scopedLoading = ref(false)
const scopedError = ref('')

const reportFieldOptions: Record<GapCReportBuilder['dataSource'], string[]> = {
  orders: ['orderNo', 'store', 'owner', 'amount', 'status'],
  expenses: ['title', 'department', 'owner', 'amount', 'status'],
  employees: ['name', 'department', 'salary', 'status'],
  audit: ['action', 'actor', 'actorId', 'object', 'at'],
}

const title = computed(() => page.value?.name['zh-CN'] ?? props.pageId)
const listPageIds = new Set(['W05', 'W06', 'W07', 'N01', 'RP01', 'U05', 'U07', 'SYS14', 'SYS15', 'SYS16', 'SYS17', 'SYS18', 'SYS22', 'SYS24'])
const isList = computed(() => listPageIds.has(props.pageId))

const matrixImpactUsers = computed(() => {
  const roles = new Set(matrix.value.filter(item => item.effect !== 'none').map(item => item.roleId))

  return [...roles].reduce((total, roleId) => total + (roleId === 'store_operator' ? 3 : 1), 0)
})

const selectedReportFields = computed(() => reportFieldOptions[reportDataSource.value])
const confirmerOptions = computed(() => gapCUsers.value.filter(user => user.status === 'active').map(user => ({ title: user.displayName, value: user.userId })))
const { confirm } = useConfirm()

function row(value: object): RowRecord {
  return value as RowRecord
}

const rows = computed<RowRecord[]>(() => {
  switch (props.pageId) {
    case 'W05': return approvals.value.filter(item => item.origin === 'agent').map(row)
    case 'W06': return approvals.value.filter(item => item.status === 'cc').map(row)
    case 'W07': return approvalRules.value.map(row)
    case 'N01': return notifications.value.map(row)
    case 'RP01': return reports.value.map(row)
    case 'U05': return auditRows.value.map(row)
    case 'U07': return alerts.value.map(row)
    case 'SYS14': return fieldPolicies.value.map(row)
    case 'SYS15': return dataScopes.value.map(row)
    case 'SYS16': return temporaryGrants.value.map(row)
    case 'SYS17': return accessReviews.value.map(row)
    case 'SYS18': return sodRules.value.map(row)
    case 'SYS22': return matrix.value.slice(0, 24).map(row)
    case 'SYS24': return changes.value.map(row)
    default: return []
  }
})

const columns = computed<ListColumn[]>(() => {
  switch (props.pageId) {
    case 'W05': return [{ key: 'title', title: '建议' }, { key: 'typeLabel', title: '类型' }, { key: 'submitter', title: '代表用户' }, { key: 'amount', title: '金额', align: 'end' }, { key: 'confidence', title: '把握度' }, { key: 'status', title: '状态' }, { key: 'actions', title: '操作' }]
    case 'W06': return [{ key: 'title', title: '单据' }, { key: 'typeLabel', title: '类型' }, { key: 'submitter', title: '提交人' }, { key: 'submittedAt', title: '时间' }, { key: 'status', title: '状态' }]
    case 'W07': return [{ key: 'type', title: '单据类型' }, { key: 'level', title: '级别' }, { key: 'minAmount', title: '起始金额' }, { key: 'maxAmount', title: '结束金额' }, { key: 'approver', title: '审批人' }, { key: 'imEnabled', title: 'IM' }]
    case 'N01': return [{ key: 'title', title: '消息' }, { key: 'category', title: '类别' }, { key: 'createdAt', title: '时间' }, { key: 'read', title: '状态' }, { key: 'actions', title: '操作' }]
    case 'RP01': return [{ key: 'name', title: '报表' }, { key: 'module', title: '模块' }, { key: 'description', title: '说明' }, { key: 'lastRunAt', title: '最近运行' }]
    case 'U05': return [{ key: 'at', title: '时间' }, { key: 'actor', title: '智能体' }, { key: 'actorId', title: '操作者 ID' }, { key: 'onBehalfOf', title: '代谁' }, { key: 'action', title: '动作' }, { key: 'objectId', title: '对象' }, { key: 'agentSuggestionId', title: '建议 ID' }]
    case 'U07': return [{ key: 'severity', title: '级别' }, { key: 'title', title: '告警' }, { key: 'detail', title: '详情' }, { key: 'createdAt', title: '时间' }, { key: 'resolved', title: '状态' }, { key: 'actions', title: '操作' }]
    case 'SYS14': return [{ key: 'roleName', title: '角色' }, { key: 'objectType', title: '对象' }, { key: 'fieldLabel', title: '字段' }, { key: 'access', title: '访问级别' }, { key: 'sensitive', title: '敏感' }]
    case 'SYS15': return [{ key: 'roleName', title: '角色' }, { key: 'objectType', title: '对象' }, { key: 'scope', title: '范围' }, { key: 'values', title: '规则值' }, { key: 'description', title: '说明' }]
    case 'SYS16': return [{ key: 'userName', title: '用户' }, { key: 'permissionKey', title: '权限点' }, { key: 'effect', title: '效果' }, { key: 'expiresAt', title: '到期' }, { key: 'status', title: '状态' }]
    case 'SYS17': return [{ key: 'userName', title: '用户' }, { key: 'reviewer', title: '复核人' }, { key: 'permissionCount', title: '权限数' }, { key: 'unusedCount', title: '长期未用' }, { key: 'dueAt', title: '截止' }, { key: 'status', title: '状态' }, { key: 'actions', title: '操作' }]
    case 'SYS18': return [{ key: 'firstAction', title: '第一动作' }, { key: 'secondAction', title: '第二动作' }, { key: 'objectType', title: '对象' }, { key: 'reason', title: '原因' }, { key: 'enabled', title: '启用' }]
    case 'SYS22': return [{ key: 'roleId', title: '角色' }, { key: 'permissionKey', title: '权限点' }, { key: 'effect', title: '效果' }, { key: 'sensitive', title: '敏感' }]
    case 'SYS24': return [{ key: 'at', title: '时间' }, { key: 'actor', title: '操作者' }, { key: 'actorId', title: '操作者 ID' }, { key: 'confirmerId', title: '确认人 ID' }, { key: 'target', title: '对象' }, { key: 'action', title: '动作' }, { key: 'before', title: '改前' }, { key: 'after', title: '改后' }]
    default: return []
  }
})

const listFilters = computed(() => {
  if (['W05', 'W06'].includes(props.pageId))
    return [{ key: 'status', label: '状态', items: [{ title: '待审批', value: 'pending' }, { title: '已通过', value: 'approved' }, { title: '已驳回', value: 'rejected' }, { title: '抄送', value: 'cc' }] }]
  if (props.pageId === 'N01')
    return [{ key: 'read', label: '阅读状态', items: [{ title: '未读', value: 'false' }, { title: '已读', value: 'true' }] }]
  if (props.pageId === 'U07')
    return [{ key: 'severity', label: '级别', items: [{ title: '高', value: 'high' }, { title: '中', value: 'medium' }, { title: '低', value: 'low' }] }]
  if (props.pageId === 'SYS16')
    return [{ key: 'status', label: '状态', items: [{ title: '有效', value: 'active' }, { title: '已过期', value: 'expired' }] }]
  if (props.pageId === 'SYS17')
    return [{ key: 'status', label: '状态', items: [{ title: '待复核', value: 'pending' }, { title: '已确认', value: 'confirmed' }, { title: '已撤销', value: 'revoked' }] }]

  return []
})

const listDateKey = computed(() => {
  if (['W05', 'W06'].includes(props.pageId))
    return 'submittedAt'
  if (props.pageId === 'N01')
    return 'createdAt'
  if (['U05', 'U07', 'SYS24'].includes(props.pageId))
    return 'at'
  if (props.pageId === 'SYS17')
    return 'dueAt'

  return ''
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    switch (props.pageId) {
      case 'W05': approvals.value = await fetchGapCApprovals('agent'); break
      case 'W06': approvals.value = await fetchGapCApprovals('cc'); break
      case 'W07': approvalRules.value = await fetchGapCApprovalRules(); break
      case 'N01': notifications.value = await fetchGapCNotifications(); break
      case 'N02': subscriptions.value = await fetchGapCSubscriptions(); break
      case 'RP01': reports.value = await fetchGapCReports(); break
      case 'RP02': reports.value = await fetchGapCReports(); break
      case 'U05': auditRows.value = await fetchGapCAudit(); break
      case 'U06': trace.value = await fetchGapCAgentTrace(typeof routeParams.id === 'string' ? routeParams.id : 'sug-001'); break
      case 'U07': alerts.value = await fetchGapCAlerts(); break
      case 'U08': retention.value = await fetchGapCRetention(); archiveRuns.value = await fetchGapCArchiveRuns(); break
      case 'SYS14': fieldPolicies.value = await fetchGapCFieldPolicies(); break
      case 'SYS15': dataScopes.value = await fetchGapCDataScopes(); break
      case 'SYS16': temporaryGrants.value = await fetchGapCTemporaryGrants(); break
      case 'SYS17': accessReviews.value = await fetchGapCAccessReviews(); break
      case 'SYS18': sodRules.value = await fetchGapCSodRules(); break
      case 'SYS21': selectedRole.value = await fetchGapCRole(typeof routeParams.id === 'string' ? routeParams.id : 'store_operator'); break
      case 'SYS22': matrix.value = await fetchGapCMatrix(); gapCUsers.value = await fetchGapCUsers(); break
      case 'SYS23': effective.value = await fetchGapCEffectivePermissions(selectedUser.value); await loadScopedPreview(); break
      case 'SYS24': changes.value = await fetchGapCPermissionChanges(); break
    }
  }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '加载失败' }
  finally { loading.value = false }
}

async function runAction(action: () => Promise<unknown>, success: string) {
  error.value = ''
  try { await action(); notice.value = success; await load() }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '操作失败' }
}

function openRow(item: RowRecord) {
  if (props.pageId === 'U05' && item.agentSuggestionId)
    router.push(`/audit/ai/${String(item.agentSuggestionId)}`)
  if (props.pageId === 'RP01')
    router.push(`/reports/${String(item.id)}`)
  if (['W05', 'W06', 'U07', 'SYS17'].includes(props.pageId)) {
    selectedRecord.value = item
    recordDrawer.value = true
  }
}

function editRule(item: RowRecord) {
  selectedRule.value = item as unknown as GapCApprovalRule
  ruleDrawer.value = true
}

async function saveSubscriptions() { await runAction(() => saveGapCSubscriptions(subscriptions.value), '订阅已保存') }
async function saveReport() {
  const builder: GapCReportBuilder = {
    dataSource: reportDataSource.value,
    fields: reportFields.value,
    filters: reportFilterValue.value ? [{ field: reportFilterField.value, operator: 'contains', value: reportFilterValue.value }] : [],
  }

  await runAction(async () => {
    const report = await createGapCReport({ name: reportName.value, description: reportDescription.value, permissionKey: 'report:read', builder })

    reportResultPreview.value = await runGapCReport(report.id, period.value)
    reportName.value = ''; reportDescription.value = ''
  }, '自定义报表已保存并生成模拟结果')
}
async function saveGrant() {
  await runAction(() => createGapCTemporaryGrant({ userId: grantUser.value, userName: grantUser.value === 'demo-operator' ? '演示运营' : '演示员工', permissionKey: grantPermission.value, effect: 'allow', reason: grantReason.value, startsAt: new Date().toISOString(), expiresAt: grantExpires.value }), '临时授权已创建')
  grantDrawer.value = false
}
async function saveRule() {
  if (!selectedRule.value)
    return
  await runAction(() => saveGapCApprovalRule(selectedRule.value!), '审批规则已保存')
  ruleDrawer.value = false
}

async function runReport() {
  const routeId = typeof routeParams.id === 'string' ? routeParams.id : ''
  const selected = reports.value.find(item => item.id === routeId) ?? reports.value[0]; if (!selected)
    return; await runAction(async () => { reportResult.value = await runGapCReport(selected.id, period.value) }, '报表已生成')
}

const reportRows = computed(() => {
  const query = reportQuery.value.trim().toLowerCase()

  return (reportResult.value?.rows ?? []).filter(item => !query || Object.values(item).some(value => String(value).toLowerCase().includes(query)))
})

function exportReport() {
  if (!reportResult.value)
    return
  const rowsToExport = reportRows.value
  const keys = Object.keys(rowsToExport[0] ?? {})
  const csv = [keys.join(','), ...rowsToExport.map(item => keys.map(key => JSON.stringify(item[key] ?? '')).join(','))].join('\n')
  const url = URL.createObjectURL(new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')

  link.href = url
  link.download = `${reportResult.value.id}.csv`
  link.click()
  URL.revokeObjectURL(url)
}
async function saveRetention() {
  if (retention.value)
    await runAction(() => saveGapCRetention(retention.value!), '保留策略已保存')
}
async function runArchive() {
  await runAction(async () => {
    const run = await runGapCArchive()

    archiveRuns.value = [run, ...archiveRuns.value]
  }, '已生成模拟归档执行记录')
}
async function saveMatrix() {
  const ok = await confirm({ title: '保存权限矩阵', text: '保存后将记录审计日志，确认继续吗？', confirmText: '确认保存', cancelText: '取消' })
  if (ok)
    await runAction(() => saveGapCMatrix(matrix.value.slice(0, 24), confirmerId.value || undefined), '权限矩阵已保存')
}
async function changeEffectiveUser() { await runAction(async () => { effective.value = await fetchGapCEffectivePermissions(selectedUser.value) }, '有效权限已刷新') }

async function loadScopedPreview() {
  scopedLoading.value = true
  scopedError.value = ''
  scopedOrders.value = []
  scopedExpenses.value = []
  scopedEmployees.value = []
  scopedContext.value = null

  const [orders, expenses, employees, context] = await Promise.allSettled([
    fetchScopedOrders(),
    fetchScopedExpenses(),
    fetchScopedEmployees(),
    fetchScopedContext(),
  ])

  scopedOrders.value = orders.status === 'fulfilled' ? orders.value : []
  scopedExpenses.value = expenses.status === 'fulfilled' ? expenses.value : []
  scopedEmployees.value = employees.status === 'fulfilled' ? employees.value : []
  scopedContext.value = context.status === 'fulfilled' ? context.value : null

  const denied: Array<[string, PromiseSettledResult<unknown>]> = [
    ['订单', orders] as [string, PromiseSettledResult<unknown>],
    ['报销', expenses] as [string, PromiseSettledResult<unknown>],
    ['员工档案', employees] as [string, PromiseSettledResult<unknown>],
  ].filter(([, result]) => result.status === 'rejected')

  if (denied.length > 0)
    scopedError.value = `${denied.map(([label, result]) => `${label}：${result.status === 'rejected' && result.reason instanceof Error ? result.reason.message : '当前主体无读取权限'}`).join('；')}。未放宽权限，表格按空结果展示。`

  scopedLoading.value = false
}

async function saveRoleCopy() {
  let copied: GapCRoleView | null = null
  await runAction(async () => {
    copied = await copyGapCRole({ sourceRoleId: selectedRole.value?.id ?? 'store_operator', nameZh: roleCopyName.value, nameEn: roleCopyNameEn.value || roleCopyName.value, dataScopes: [roleCopyScope.value as GapCRoleView['defaultDataScopes'][number]], memberUserIds: roleCopyUsers.value.split(/[,，]/).map(item => item.trim()).filter(Boolean) })
    roleCopyDrawer.value = false
    roleCopyName.value = ''; roleCopyNameEn.value = ''; roleCopyUsers.value = 'demo-operator'
  }, '角色已复制、保存并模拟指派用户')
  if (copied)
    selectedRole.value = copied
}

function changeReportSource(value: GapCReportBuilder['dataSource']) {
  reportDataSource.value = value
  reportFields.value = reportFieldOptions[value].slice(0, 4)
  reportFilterField.value = reportFieldOptions[value][0]
}

watch(() => session.role, () => {
  if (props.pageId === 'SYS23')
    load()
})

onMounted(load)
</script>

<template>
  <div>
    <VAlert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-4"
    >
      {{ error }}
    </VAlert>
    <VAlert
      v-if="notice"
      type="success"
      variant="tonal"
      closable
      class="mb-4"
      @click:close="notice = ''"
    >
      {{ notice }}
    </VAlert>

    <ListPage
      v-if="isList"
      :storage-key="`gap-c-${props.pageId}`"
      :title="title"
      :subtitle="page?.purpose['zh-CN']"
      :items="rows"
      :columns="columns"
      :filters="listFilters"
      :date-key="listDateKey"
      :loading="loading"
      :error="error"
      @retry="load"
      @open="openRow"
    >
      <template #widgets>
        <div
          v-if="props.pageId === 'SYS16'"
          class="d-flex justify-end mb-4"
        >
          <PermissionGate action="create">
            <VBtn
              color="primary"
              @click="grantDrawer = true"
            >
              新增临时授权
            </VBtn>
          </PermissionGate>
        </div>
        <VAlert
          v-if="props.pageId === 'SYS22'"
          type="warning"
          variant="tonal"
          class="mb-4"
        >
          敏感权限保存前必须填写另一位管理员的确认身份；拒绝优先。
        </VAlert>
        <div
          v-if="props.pageId === 'SYS22'"
          class="d-flex gap-4 align-center mb-4"
        >
          <VChip
            color="info"
            variant="tonal"
          >
            预计影响用户数：{{ matrixImpactUsers }}
          </VChip>
          <AppSelect
            v-model="confirmerId"
            label="另一位管理员确认人"
            :items="confirmerOptions"
            placeholder="请选择真实用户"
            clearable
          />
          <PermissionGate action="update">
            <VBtn
              color="primary"
              @click="saveMatrix"
            >
              保存矩阵
            </VBtn>
          </PermissionGate>
        </div>
      </template>
      <template #item.amount="{ item }">
        <MoneyText
          v-if="typeof item.amount === 'number'"
          :amount="item.amount"
          minor
          currency="CNY"
        />
      </template>
      <template #item.status="{ item }">
        <StatusChip
          :domain="['W05', 'W06'].includes(props.pageId) ? 'approval' : 'generic'"
          :value="String(item.status)"
        />
      </template>
      <template #item.actions="{ item }">
        <VBtn
          v-if="props.pageId === 'W05'"
          size="small"
          color="primary"
          variant="tonal"
          @click="openRow(item)"
        >
          查看并处理
        </VBtn>
        <VBtn
          v-else-if="props.pageId === 'W07'"
          size="small"
          variant="text"
          @click="editRule(item)"
        >
          编辑
        </VBtn>
        <VBtn
          v-else-if="props.pageId === 'N01' && !item.read"
          size="small"
          variant="text"
          @click="runAction(() => markGapCNotificationRead(String(item.id)), '消息已读')"
        >
          标为已读
        </VBtn>
        <VBtn
          v-else-if="props.pageId === 'U07' && !item.resolved"
          size="small"
          variant="text"
          @click="runAction(() => resolveGapCAlert(String(item.id)), '告警已处理')"
        >
          处理
        </VBtn>
        <VBtn
          v-else-if="props.pageId === 'SYS17' && item.status === 'pending'"
          size="small"
          variant="text"
          @click="runAction(() => confirmGapCAccessReview(String(item.id)), '权限复核已确认')"
        >
          确认复核
        </VBtn>
      </template>
      <template #item.access="{ item }">
        <AppSelect
          :model-value="item.access"
          :items="['hidden', 'masked', 'readonly', 'visible']"
          density="compact"
          hide-details
          @update:model-value="runAction(() => saveGapCFieldPolicy(String(item.id), $event as FieldAccess), '字段权限已保存')"
        />
      </template>
      <template #item.scope="{ item }">
        <AppSelect
          :model-value="item.scope"
          :items="['all', 'store', 'department', 'self', 'owner', 'warehouse', 'amount']"
          density="compact"
          hide-details
          @update:model-value="runAction(() => saveGapCDataScope(String(item.id), $event), '数据范围已保存')"
        />
      </template>
      <template #item.enabled="{ item }">
        <VSwitch
          :model-value="Boolean(item.enabled)"
          hide-details
          density="compact"
          @update:model-value="runAction(() => saveGapCSodRule(String(item.id), Boolean($event)), '职责分离规则已保存')"
        />
      </template>
      <template #item.effect="{ item }">
        <AppSelect
          :model-value="item.effect"
          :items="['allow', 'inherit', 'deny', 'none']"
          density="compact"
          hide-details
          @update:model-value="item.effect = $event"
        />
      </template>
    </ListPage>

    <FormPage
      v-else-if="props.pageId === 'N02'"
      :title="title"
      :subtitle="page?.purpose['zh-CN']"
      @save="saveSubscriptions"
      @cancel="load"
    >
      <template #default>
        <VTable>
          <thead><tr><th>事件</th><th>说明</th><th>站内</th><th>飞书</th><th>企业微信</th><th>邮件</th></tr></thead>
          <tbody>
            <tr
              v-for="item in subscriptions"
              :key="item.id"
            >
              <td>{{ item.event }}</td><td>{{ item.description }}</td><td>
                <VSwitch
                  v-model="item.inApp"
                  hide-details
                />
              </td><td>
                <VSwitch
                  v-model="item.feishu"
                  hide-details
                />
              </td><td>
                <VSwitch
                  v-model="item.wecom"
                  hide-details
                />
              </td><td>
                <VSwitch
                  v-model="item.email"
                  hide-details
                />
              </td>
            </tr>
          </tbody>
        </VTable>
      </template>
    </FormPage>

    <DetailPage
      v-else-if="props.pageId === 'RP02'"
      :title="title"
      :subtitle="page?.purpose['zh-CN']"
    >
      <template #actions>
        <AppSelect
          v-model="period"
          label="期间"
          :items="['2026-09', '2026-10', '2026-11']"
        />
        <VBtn
          color="primary"
          @click="runReport"
        >
          运行报表
        </VBtn>
        <AppTextField
          v-if="reportResult"
          v-model="reportQuery"
          label="筛选结果"
          density="compact"
        />
        <VBtn
          v-if="reportResult"
          variant="tonal"
          prepend-icon="tabler-download"
          @click="exportReport"
        >
          导出 CSV
        </VBtn>
      </template>
      <template #default>
        <VRow v-if="reportResult">
          <VCol
            v-for="(value, key) in reportResult.totals"
            :key="key"
            cols="12"
            sm="4"
          >
            <KpiCard
              :title="String(key)"
              :value="String(value)"
              icon="tabler-report-analytics"
            />
          </VCol>
        </VRow>
        <VTable
          v-if="reportResult"
          class="mt-6"
        >
          <thead>
            <tr>
              <th
                v-for="key in Object.keys(reportResult.rows[0] ?? {})"
                :key="key"
              >
                {{ key }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(item, index) in reportRows"
              :key="index"
            >
              <td
                v-for="key in Object.keys(item)"
                :key="key"
              >
                {{ item[key] }}
              </td>
            </tr>
          </tbody>
        </VTable>
        <EmptyState
          v-else
          text="选择期间并运行报表后查看结果。"
        />
      </template>
    </DetailPage>

    <FormPage
      v-else-if="props.pageId === 'RP03'"
      :title="title"
      :subtitle="page?.purpose['zh-CN']"
      @save="saveReport"
      @cancel="() => { reportName = ''; reportDescription = '' }"
    >
      <template #default>
        <AppTextField
          v-model="reportName"
          label="报表名称"
          class="mb-4"
          :rules="[requiredValidator]"
        /><AppTextarea
          v-model="reportDescription"
          label="说明"
          class="mb-4"
        />
        <AppSelect
          :model-value="reportDataSource"
          label="数据源（模拟）"
          :items="[{ title: '订单', value: 'orders' }, { title: '费用报销', value: 'expenses' }, { title: '员工档案', value: 'employees' }, { title: '审计日志', value: 'audit' }]"
          class="mb-4"
          @update:model-value="changeReportSource($event as GapCReportBuilder['dataSource'])"
        />
        <AppSelect
          v-model="reportFields"
          label="字段（模拟）"
          :items="selectedReportFields"
          multiple
          chips
          class="mb-4"
        />
        <VRow>
          <VCol
            cols="12"
            md="6"
          >
            <AppSelect
              v-model="reportFilterField"
              label="筛选字段（可选）"
              :items="selectedReportFields"
            />
          </VCol>
          <VCol
            cols="12"
            md="6"
          >
            <AppTextField
              v-model="reportFilterValue"
              label="筛选值（可选）"
            />
          </VCol>
        </VRow>
        <VAlert
          v-if="reportResultPreview"
          type="success"
          variant="tonal"
          class="mt-4"
        >
          模拟结果已生成：{{ reportResultPreview.rows.length }} 行，期间 {{ reportResultPreview.period }}；保存、运行和审计记录均为模拟。
          <VTable class="mt-3">
            <thead>
              <tr>
                <th
                  v-for="key in Object.keys(reportResultPreview.rows[0] ?? {})"
                  :key="key"
                >
                  {{ key }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(item, index) in reportResultPreview.rows"
                :key="index"
              >
                <td
                  v-for="key in Object.keys(item)"
                  :key="key"
                >
                  {{ item[key] }}
                </td>
              </tr>
            </tbody>
          </VTable>
        </VAlert>
      </template>
    </FormPage>

    <DetailPage
      v-else-if="props.pageId === 'U06' && trace"
      :title="trace.actor"
      :subtitle="`${trace.question} · 代 ${trace.onBehalfOf}`"
    >
      <template #default>
        <VAlert
          type="info"
          variant="tonal"
          class="mb-4"
        >
          建议 {{ trace.suggestionId }} · {{ trace.level }} · 把握度 {{ trace.confidence }}
        </VAlert><VTimeline
          density="compact"
          align="start"
        >
          <VTimelineItem
            v-for="item in trace.steps"
            :key="item.at"
            :dot-color="item.status === 'ok' ? 'success' : 'warning'"
          >
            <div class="font-weight-medium">
              {{ item.title }}
            </div><div class="text-body-2">
              {{ item.detail }}
            </div>
          </VTimelineItem>
        </VTimeline><VAlert
          type="success"
          variant="tonal"
        >
          结果：{{ trace.outcome }}
        </VAlert>
      </template>
    </DetailPage>

    <FormPage
      v-else-if="props.pageId === 'U08' && retention"
      :title="title"
      :subtitle="page?.purpose['zh-CN']"
      @save="saveRetention"
      @cancel="load"
    >
      <template #default>
        <VAlert
          type="info"
          variant="tonal"
          class="mb-4"
        >
          审计日志只追加，不能删除；当前策略按业务日志 10 年、AI 明细 3 年保留。
        </VAlert><VRow>
          <VCol
            cols="12"
            md="4"
          >
            <AppTextField
              v-model.number="retention.businessYears"
              type="number"
              label="业务日志保留年数"
            />
          </VCol><VCol
            cols="12"
            md="4"
          >
            <AppTextField
              v-model.number="retention.aiYears"
              type="number"
              label="AI 明细保留年数"
            />
          </VCol><VCol
            cols="12"
            md="4"
          >
            <AppTextField
              v-model.number="retention.archiveAfterDays"
              type="number"
              label="归档等待天数"
            />
          </VCol>
        </VRow>
        <VBtn
          color="primary"
          variant="tonal"
          class="mt-4"
          @click="runArchive"
        >
          模拟执行归档
        </VBtn>
        <VTable class="mt-4">
          <thead><tr><th>执行时间</th><th>归档条数</th><th>状态</th><th>说明</th></tr></thead>
          <tbody>
            <tr
              v-for="run in archiveRuns"
              :key="run.id"
            >
              <td>{{ run.startedAt }}</td><td>{{ run.archivedCount }}</td><td>{{ run.status }}</td><td>{{ run.note }}</td>
            </tr>
          </tbody>
        </VTable>
      </template>
    </FormPage>

    <DetailPage
      v-else-if="props.pageId === 'SYS21' && selectedRole"
      :title="selectedRole.nameZh"
      :subtitle="`角色 ${selectedRole.id} · 成员 ${selectedRole.memberCount} 人`"
      domain="generic"
      :status="selectedRole.status"
    >
      <template #actions>
        <PermissionGate action="create">
          <VBtn
            variant="tonal"
            @click="roleCopyDrawer = true"
          >
            复制并保存角色
          </VBtn>
        </PermissionGate>
      </template>
      <template #default>
        <div class="d-flex gap-2 mb-4">
          <VChip
            color="primary"
            variant="tonal"
          >
            {{ selectedRole.id }}
          </VChip><VChip variant="tonal">
            成员 {{ selectedRole.memberCount }} 人
          </VChip>
        </div><p>父角色：{{ selectedRole.parentIds.length ? selectedRole.parentIds.join('、') : '无' }}</p><p>ERPNext：{{ selectedRole.erpnextRefs.join('、') }}</p><p>Odoo：{{ selectedRole.odooRefs.join('、') }}</p><VDivider class="my-4" /><div class="text-subtitle-1 mb-2">
          本角色权限
        </div><VChip
          v-for="item in selectedRole.permissions.slice(0, 20)"
          :key="`${item.permissionKey}-${item.source}`"
          class="ma-1"
          size="small"
          variant="tonal"
        >
          {{ item.permissionKey }} · {{ item.effect === 'allow' ? '允许' : '拒绝' }}
        </VChip>
        <VAlert
          v-if="selectedRole.isCustom"
          type="info"
          variant="tonal"
          class="mt-4"
        >
          已保存模拟角色：数据范围 {{ selectedRole.dataScopeLabel }}；指派用户 {{ selectedRole.memberUserIds?.join('、') || '无' }}。这些用户的菜单和数据范围会随角色刷新（静态原型）。
        </VAlert>
      </template>
    </DetailPage>

    <DetailPage
      v-else-if="props.pageId === 'SYS23'"
      :title="title"
      :subtitle="page?.purpose['zh-CN']"
    >
      <template #actions>
        <AppSelect
          v-model="selectedUser"
          label="用户"
          :items="[{ title: '演示运营', value: 'demo-operator' }, { title: '演示财务', value: 'demo-finance' }, { title: '演示员工', value: 'demo-employee' }]"
        />
        <VBtn
          color="primary"
          @click="changeEffectiveUser"
        >
          查看有效权限
        </VBtn>
      </template>
      <template #default>
        <VTable>
          <thead><tr><th>权限点</th><th>模块</th><th>结果</th><th>来源</th><th>拒绝原因</th></tr></thead><tbody>
            <tr
              v-for="item in effective"
              :key="item.permissionKey"
            >
              <td>
                {{ item.labelZh }}<VChip
                  v-if="item.sensitive"
                  size="x-small"
                  color="error"
                  class="ms-2"
                >
                  敏感
                </VChip>
              </td><td>{{ item.module }}</td><td>
                <StatusChip
                  domain="generic"
                  :value="item.allowed ? 'active' : 'disabled'"
                />
              </td><td>{{ item.sources.join('；') || '—' }}</td><td>{{ item.deniedBy.join('；') || '—' }}</td>
            </tr>
          </tbody>
        </VTable>
        <VCard
          class="mt-6"
          variant="outlined"
        >
          <VCardItem>
            <VCardTitle>当前身份可见数据预览</VCardTitle>
            <VCardSubtitle>以下数据由当前会话身份调用 scoped read API 返回，切换顶栏角色后自动刷新。</VCardSubtitle>
          </VCardItem>
          <VCardText>
            <VAlert
              v-if="scopedError"
              type="error"
              variant="tonal"
              class="mb-4"
            >
              {{ scopedError }}
            </VAlert>
            <VProgressLinear
              v-if="scopedLoading"
              indeterminate
              class="mb-4"
            />
            <div class="d-flex flex-wrap align-center gap-3 mb-4">
              <VChip
                color="primary"
                variant="tonal"
              >
                主体：{{ session.displayName }}（{{ session.userId }}）
              </VChip>
              <StatusChip
                domain="generic"
                value="active"
              />
              <span v-if="scopedContext">数据范围：订单 {{ scopedContext.dataScopes.orders.join('、') || '无' }}；报销 {{ scopedContext.dataScopes.expenses.join('、') || '无' }}；员工档案 {{ scopedContext.dataScopes.employees.join('、') || '无' }}</span>
              <span v-else>数据范围：加载中</span>
              <span>绑定店铺：{{ scopedContext?.shopsForSubject.join('、') || '无' }}</span>
            </div>
            <VRow>
              <VCol
                cols="12"
                md="4"
              >
                <VCard variant="tonal">
                  <VCardItem>
                    <VCardTitle>订单</VCardTitle>
                    <VCardSubtitle>{{ scopedOrders.length }} 条</VCardSubtitle>
                  </VCardItem>
                  <VTable
                    data-testid="scope-preview-orders"
                    density="compact"
                  >
                    <thead><tr><th>id</th><th>orderNo</th><th>shopId</th><th>ownerId</th><th>department</th></tr></thead>
                    <tbody>
                      <tr
                        v-for="item in scopedOrders"
                        :key="item.id"
                        :data-shop="item.shopId"
                        :data-owner="item.ownerId"
                      >
                        <td>{{ item.id }}</td><td>{{ item.orderNo }}</td><td>{{ item.shopId }}</td><td>{{ item.ownerId }}</td><td>{{ item.department }}</td>
                      </tr>
                    </tbody>
                  </VTable>
                </VCard>
              </VCol>
              <VCol
                cols="12"
                md="4"
              >
                <VCard variant="tonal">
                  <VCardItem>
                    <VCardTitle>报销</VCardTitle>
                    <VCardSubtitle>{{ scopedExpenses.length }} 条</VCardSubtitle>
                  </VCardItem>
                  <VTable
                    data-testid="scope-preview-expenses"
                    density="compact"
                  >
                    <thead><tr><th>id</th><th>title</th><th>shopId</th><th>ownerId</th><th>department</th></tr></thead>
                    <tbody>
                      <tr
                        v-for="item in scopedExpenses"
                        :key="item.id"
                        :data-shop="item.shopId"
                        :data-owner="item.ownerId"
                      >
                        <td>{{ item.id }}</td><td>{{ item.title }}</td><td>{{ item.shopId }}</td><td>{{ item.ownerId }}</td><td>{{ item.department }}</td>
                      </tr>
                    </tbody>
                  </VTable>
                </VCard>
              </VCol>
              <VCol
                cols="12"
                md="4"
              >
                <VCard variant="tonal">
                  <VCardItem>
                    <VCardTitle>员工档案</VCardTitle>
                    <VCardSubtitle>{{ scopedEmployees.length }} 条</VCardSubtitle>
                  </VCardItem>
                  <VTable
                    data-testid="scope-preview-employees"
                    density="compact"
                  >
                    <thead><tr><th>id</th><th>name</th><th>shopId</th><th>ownerId</th><th>department</th></tr></thead>
                    <tbody>
                      <tr
                        v-for="item in scopedEmployees"
                        :key="item.id"
                        :data-shop="item.shopId"
                        :data-owner="item.ownerId"
                      >
                        <td>{{ item.id }}</td><td>{{ item.name }}</td><td>{{ item.shopId }}</td><td>{{ item.ownerId }}</td><td>{{ item.department }}</td>
                      </tr>
                    </tbody>
                  </VTable>
                </VCard>
              </VCol>
            </VRow>
          </VCardText>
        </VCard>
      </template>
    </DetailPage>

    <RecordDrawer
      v-model="recordDrawer"
      :title="String(selectedRecord?.title || selectedRecord?.userName || selectedRecord?.id || title)"
    >
      <template v-if="selectedRecord">
        <div class="d-flex align-center gap-2 mb-4">
          <StatusChip
            v-if="selectedRecord.status"
            :domain="['W05', 'W06'].includes(props.pageId) ? 'approval' : 'generic'"
            :value="String(selectedRecord.status)"
          />
          <span v-if="selectedRecord.severity">级别：{{ selectedRecord.severity }}</span>
        </div>
        <p v-if="selectedRecord.summary">
          {{ selectedRecord.summary }}
        </p>
        <p v-if="selectedRecord.detail">
          {{ selectedRecord.detail }}
        </p>
        <p v-if="selectedRecord.userName">
          用户：{{ selectedRecord.userName }}
        </p>
        <p v-if="selectedRecord.reviewer">
          复核人：{{ selectedRecord.reviewer }}
        </p>
        <MoneyText
          v-if="typeof selectedRecord.amount === 'number'"
          :amount="selectedRecord.amount"
          :currency="typeof selectedRecord.currency === 'string' ? selectedRecord.currency as 'CNY' : 'CNY'"
          minor
        />
        <div class="d-flex gap-3 mt-4">
          <PermissionGate
            v-if="props.pageId === 'W05'"
            action="approve"
          >
            <VBtn
              color="success"
              :disabled="selectedRecord.status !== 'pending'"
              @click="runAction(() => decideGapCApproval(String(selectedRecord?.id), 'approved'), '建议已批准').then(() => { recordDrawer = false })"
            >
              批准
            </VBtn>
            <VBtn
              color="error"
              variant="tonal"
              :disabled="selectedRecord.status !== 'pending'"
              @click="runAction(() => decideGapCApproval(String(selectedRecord?.id), 'rejected'), '建议已驳回').then(() => { recordDrawer = false })"
            >
              驳回
            </VBtn>
          </PermissionGate>
          <PermissionGate
            v-if="props.pageId === 'U07' && !selectedRecord.resolved"
            action="update"
          >
            <VBtn
              color="primary"
              @click="runAction(() => resolveGapCAlert(String(selectedRecord?.id)), '告警已处理').then(() => { recordDrawer = false })"
            >
              标记已处理
            </VBtn>
          </PermissionGate>
          <PermissionGate
            v-if="props.pageId === 'SYS17' && selectedRecord.status === 'pending'"
            action="approve"
          >
            <VBtn
              color="primary"
              @click="runAction(() => confirmGapCAccessReview(String(selectedRecord?.id)), '权限复核已确认').then(() => { recordDrawer = false })"
            >
              确认复核
            </VBtn>
          </PermissionGate>
        </div>
      </template>
    </RecordDrawer>

    <FormDrawer
      v-model="grantDrawer"
      title="新增临时授权"
      @save="saveGrant"
    >
      <AppSelect
        v-model="grantUser"
        label="用户"
        :items="[{ title: '演示运营', value: 'demo-operator' }, { title: '演示员工', value: 'demo-employee' }]"
        class="mb-4"
      />
      <AppTextField
        v-model="grantPermission"
        label="权限点"
        class="mb-4"
      />
      <AppTextField
        v-model="grantExpires"
        label="到期时间"
        class="mb-4"
      />
      <AppTextField
        v-model="grantReason"
        label="原因"
      />
    </FormDrawer>

    <FormDrawer
      v-model="roleCopyDrawer"
      title="复制并保存角色（模拟）"
      @save="saveRoleCopy"
    >
      <VAlert
        type="info"
        variant="tonal"
        class="mb-4"
      >
        复制会保留父角色继承和显式拒绝；修改后的数据范围、用户指派和审计记录均在 mock 中保存。
      </VAlert>
      <AppTextField
        v-model="roleCopyName"
        label="新角色中文名"
        class="mb-4"
        :rules="[requiredValidator]"
      />
      <AppTextField
        v-model="roleCopyNameEn"
        label="新角色英文名"
        class="mb-4"
        :rules="[requiredValidator]"
      />
      <AppSelect
        v-model="roleCopyScope"
        label="数据范围"
        :items="[{ title: '欧洲店铺', value: 'store' }, { title: '本部门', value: 'department' }, { title: '本人', value: 'self' }, { title: '全部', value: 'all' }]"
        class="mb-4"
      />
      <AppTextField
        v-model="roleCopyUsers"
        label="指派用户（逗号分隔）"
      />
    </FormDrawer>

    <FormDrawer
      v-model="ruleDrawer"
      title="编辑审批规则"
      @save="saveRule"
    >
      <template v-if="selectedRule">
        <AppTextField
          v-model="selectedRule.type"
          label="单据类型"
          class="mb-4"
        />
        <AppTextField
          v-model.number="selectedRule.level"
          type="number"
          label="审批级别"
          class="mb-4"
        />
        <AppTextField
          v-model.number="selectedRule.minAmount"
          type="number"
          label="起始金额"
          class="mb-4"
        />
        <AppTextField
          v-model.number="selectedRule.maxAmount"
          type="number"
          label="结束金额"
          class="mb-4"
        />
        <AppTextField
          v-model="selectedRule.approver"
          label="审批人"
          class="mb-4"
        />
        <VSwitch
          v-model="selectedRule.imEnabled"
          label="允许 IM 审批"
        />
      </template>
    </FormDrawer>

    <VAlert
      v-if="props.pageId === 'W05' && aiMode.isEnabled"
      type="info"
      variant="tonal"
      class="mt-4"
    >
      智能体只创建建议，审批必须由真人完成；关闭 AI 总开关后，人工审批路径仍可继续。
    </VAlert>
    <PermissionGate
      v-if="loading"
      action="view"
    >
      <VProgressLinear
        indeterminate
        class="mt-4"
      />
    </PermissionGate>
  </div>
</template>
