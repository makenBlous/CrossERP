<script setup lang="ts">
/* eslint-disable indent, max-statements-per-line */
import { computed, onMounted, ref } from 'vue'
import {
  confirmGapCAccessReview,
  createGapCReport,
  createGapCTemporaryGrant,
  decideGapCApproval,
  fetchGapCAccessReviews,
  fetchGapCAgentTrace,
  fetchGapCAlerts,
  fetchGapCApprovalRules,
  fetchGapCApprovals,
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
  markGapCNotificationRead,
  resolveGapCAlert,
  runGapCReport,
  saveGapCDataScope,
  saveGapCFieldPolicy,
  saveGapCMatrix,
  saveGapCRetention,
  saveGapCSodRule,
  saveGapCSubscriptions,
} from '@/api/gap-c'
import DetailPage from '@/components/biz/DetailPage.vue'
import ListPage, { type ListColumn } from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import { findPageById } from '@/config/pages'
import { useAiModeStore } from '@/stores/ai-mode'
import type { FieldAccess } from '@/types/gap-c'
import type { GapCAccessReview, GapCAgentTrace, GapCAlert, GapCApprovalRow, GapCApprovalRule, GapCAuditRow, GapCDataScope, GapCFieldPolicy, GapCMatrixCell, GapCNotification, GapCPermissionChange, GapCReport, GapCReportResult, GapCRetention, GapCRoleView, GapCSodRule, GapCSubscription, GapCTemporaryGrant } from '@/types/gap-c'

interface RowRecord { id: string; [key: string]: unknown }

const props = defineProps<{ pageId: string }>()
const router = useRouter()
const route = useRoute()
const routeParams = route.params as Record<string, string | string[] | undefined>
const aiMode = useAiModeStore()
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
const fieldPolicies = ref<GapCFieldPolicy[]>([])
const dataScopes = ref<GapCDataScope[]>([])
const temporaryGrants = ref<GapCTemporaryGrant[]>([])
const accessReviews = ref<GapCAccessReview[]>([])
const selectedRole = ref<GapCRoleView | null>(null)
const matrix = ref<GapCMatrixCell[]>([])
const effective = ref<Array<{ permissionKey: string; labelZh: string; allowed: boolean; sources: string[]; deniedBy: string[]; module: string; sensitive: boolean }>>([])
const changes = ref<GapCPermissionChange[]>([])
const sodRules = ref<GapCSodRule[]>([])
const selectedUser = ref('demo-operator')
const period = ref('2026-11')
const confirmer = ref('')
const reportName = ref('')
const reportDescription = ref('')
const grantUser = ref('demo-operator')
const grantPermission = ref('sku_cost:read')
const grantReason = ref('')
const grantExpires = ref('2026-11-17T00:00:00Z')

const title = computed(() => page.value?.name['zh-CN'] ?? props.pageId)
const listPageIds = new Set(['W05', 'W06', 'W07', 'N01', 'RP01', 'U05', 'U07', 'SYS14', 'SYS15', 'SYS17', 'SYS18', 'SYS24'])
const isList = computed(() => listPageIds.has(props.pageId))

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
    case 'U05': return [{ key: 'at', title: '时间' }, { key: 'actor', title: '智能体' }, { key: 'onBehalfOf', title: '代谁' }, { key: 'action', title: '动作' }, { key: 'objectId', title: '对象' }, { key: 'agentSuggestionId', title: '建议 ID' }]
    case 'U07': return [{ key: 'severity', title: '级别' }, { key: 'title', title: '告警' }, { key: 'detail', title: '详情' }, { key: 'createdAt', title: '时间' }, { key: 'resolved', title: '状态' }, { key: 'actions', title: '操作' }]
    case 'SYS14': return [{ key: 'roleName', title: '角色' }, { key: 'objectType', title: '对象' }, { key: 'fieldLabel', title: '字段' }, { key: 'access', title: '访问级别' }, { key: 'sensitive', title: '敏感' }]
    case 'SYS15': return [{ key: 'roleName', title: '角色' }, { key: 'objectType', title: '对象' }, { key: 'scope', title: '范围' }, { key: 'values', title: '规则值' }, { key: 'description', title: '说明' }]
    case 'SYS16': return [{ key: 'userName', title: '用户' }, { key: 'permissionKey', title: '权限点' }, { key: 'effect', title: '效果' }, { key: 'expiresAt', title: '到期' }, { key: 'status', title: '状态' }]
    case 'SYS17': return [{ key: 'userName', title: '用户' }, { key: 'reviewer', title: '复核人' }, { key: 'permissionCount', title: '权限数' }, { key: 'unusedCount', title: '长期未用' }, { key: 'dueAt', title: '截止' }, { key: 'status', title: '状态' }, { key: 'actions', title: '操作' }]
    case 'SYS18': return [{ key: 'firstAction', title: '第一动作' }, { key: 'secondAction', title: '第二动作' }, { key: 'objectType', title: '对象' }, { key: 'reason', title: '原因' }, { key: 'enabled', title: '启用' }]
    case 'SYS22': return [{ key: 'roleId', title: '角色' }, { key: 'permissionKey', title: '权限点' }, { key: 'effect', title: '效果' }, { key: 'sensitive', title: '敏感' }]
    case 'SYS24': return [{ key: 'at', title: '时间' }, { key: 'actor', title: '操作者' }, { key: 'target', title: '对象' }, { key: 'action', title: '动作' }, { key: 'before', title: '改前' }, { key: 'after', title: '改后' }]
    default: return []
  }
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
      case 'U08': retention.value = await fetchGapCRetention(); break
      case 'SYS14': fieldPolicies.value = await fetchGapCFieldPolicies(); break
      case 'SYS15': dataScopes.value = await fetchGapCDataScopes(); break
      case 'SYS16': temporaryGrants.value = await fetchGapCTemporaryGrants(); break
      case 'SYS17': accessReviews.value = await fetchGapCAccessReviews(); break
      case 'SYS18': sodRules.value = await fetchGapCSodRules(); break
      case 'SYS21': selectedRole.value = await fetchGapCRole(typeof routeParams.id === 'string' ? routeParams.id : 'store_operator'); break
      case 'SYS22': matrix.value = await fetchGapCMatrix(); break
      case 'SYS23': effective.value = await fetchGapCEffectivePermissions(selectedUser.value); break
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
}

async function saveSubscriptions() { await runAction(() => saveGapCSubscriptions(subscriptions.value), '订阅已保存') }
async function saveReport() { await runAction(async () => { await createGapCReport({ name: reportName.value, description: reportDescription.value, permissionKey: 'report:read' }); reportName.value = ''; reportDescription.value = '' }, '自定义报表已保存') }
async function saveGrant() { await runAction(() => createGapCTemporaryGrant({ userId: grantUser.value, userName: grantUser.value === 'demo-operator' ? '演示运营' : '演示员工', permissionKey: grantPermission.value, effect: 'allow', reason: grantReason.value, startsAt: new Date().toISOString(), expiresAt: grantExpires.value }), '临时授权已创建') }
async function runReport() {
  const selected = reports.value[0]; if (!selected)
    return; await runAction(async () => { reportResult.value = await runGapCReport(selected.id, period.value) }, '报表已生成')
}
async function saveRetention() {
  if (retention.value)
    await runAction(() => saveGapCRetention(retention.value!), '保留策略已保存')
}
async function saveMatrix() { await runAction(() => saveGapCMatrix(matrix.value.slice(0, 24), confirmer.value), '权限矩阵已保存') }
async function changeEffectiveUser() { await runAction(async () => { effective.value = await fetchGapCEffectivePermissions(selectedUser.value) }, '有效权限已刷新') }

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
      :loading="loading"
      @open="openRow"
    >
      <template #item.amount="{ item }">
        <MoneyText
          v-if="typeof item.amount === 'number'"
          :amount="item.amount"
          minor
          currency="CNY"
        />
      </template>
      <template #item.status="{ item }">
        <VChip
          size="small"
          :color="item.status === 'approved' || item.status === 'confirmed' || item.status === 'read' ? 'success' : item.status === 'rejected' || item.status === 'expired' ? 'error' : 'warning'"
          variant="tonal"
        >
          {{ item.status === 'pending' ? '待处理' : item.status === 'cc' ? '抄送' : item.status === 'read' ? '已读' : item.status === 'active' ? '有效' : String(item.status) }}
        </VChip>
      </template>
      <template #item.actions="{ item }">
        <VBtn
          v-if="props.pageId === 'W05'"
          size="small"
          color="primary"
          variant="tonal"
          @click="runAction(() => decideGapCApproval(String(item.id), 'approved'), '建议已批准')"
        >
          批准
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
    </ListPage>

    <VCard
      v-else-if="props.pageId === 'N02'"
      :title="title"
    >
      <VCardText>
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
        <VBtn
          class="mt-4"
          color="primary"
          @click="saveSubscriptions"
        >
          保存订阅
        </VBtn>
      </VCardText>
    </VCard>

    <VCard
      v-else-if="props.pageId === 'RP02'"
      :title="title"
    >
      <VCardText>
        <div class="d-flex gap-4 align-center">
          <AppSelect
            v-model="period"
            label="期间"
            :items="['2026-09', '2026-10', '2026-11']"
          /><VBtn
            color="primary"
            @click="runReport"
          >
            运行报表
          </VBtn>
        </div><VTable
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
          </thead><tbody>
            <tr
              v-for="(item, index) in reportResult.rows"
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
      </VCardText>
    </VCard>

    <VCard
      v-else-if="props.pageId === 'RP03'"
      :title="title"
    >
      <VCardText>
        <AppTextField
          v-model="reportName"
          label="报表名称"
          class="mb-4"
        /><AppTextarea
          v-model="reportDescription"
          label="说明"
          class="mb-4"
        /><VBtn
          color="primary"
          @click="saveReport"
        >
          保存报表
        </VBtn>
      </VCardText>
    </VCard>

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

    <VCard
      v-else-if="props.pageId === 'U08' && retention"
      :title="title"
    >
      <VCardText>
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
        </VRow><VBtn
          color="primary"
          class="mt-4"
          @click="saveRetention"
        >
          保存策略
        </VBtn>
      </VCardText>
    </VCard>

    <VCard
      v-else-if="props.pageId === 'SYS16'"
      title="新增临时授权"
      class="mb-6"
    >
      <VCardText>
        <VRow>
          <VCol
            cols="12"
            md="3"
          >
            <AppSelect
              v-model="grantUser"
              label="用户"
              :items="[{ title: '演示运营', value: 'demo-operator' }, { title: '演示员工', value: 'demo-employee' }]"
            />
          </VCol><VCol
            cols="12"
            md="3"
          >
            <AppTextField
              v-model="grantPermission"
              label="权限点"
            />
          </VCol><VCol
            cols="12"
            md="3"
          >
            <AppTextField
              v-model="grantExpires"
              label="到期时间"
            />
          </VCol><VCol
            cols="12"
            md="3"
          >
            <AppTextField
              v-model="grantReason"
              label="原因"
            />
          </VCol>
        </VRow><VBtn
          color="primary"
          @click="saveGrant"
        >
          创建授权
        </VBtn>
        <VTable class="mt-6">
          <thead><tr><th>用户</th><th>权限点</th><th>原因</th><th>到期</th><th>状态</th></tr></thead>
          <tbody><tr v-for="item in temporaryGrants" :key="item.id"><td>{{ item.userName }}</td><td>{{ item.permissionKey }}</td><td>{{ item.reason }}</td><td>{{ item.expiresAt }}</td><td>{{ item.status }}</td></tr></tbody>
        </VTable>
      </VCardText>
    </VCard>

    <VCard
      v-else-if="props.pageId === 'SYS21' && selectedRole"
      :title="selectedRole.nameZh"
    >
      <VCardText>
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
        </VChip><VBtn
          class="mt-4"
          variant="tonal"
          @click="notice = '复制角色会创建新角色草稿，需管理员确认后保存。'"
        >
          复制为新角色
        </VBtn>
      </VCardText>
    </VCard>

    <VCard
      v-else-if="props.pageId === 'SYS23'"
      :title="title"
    >
      <VCardText>
        <div class="d-flex gap-4 align-center mb-4">
          <AppSelect
            v-model="selectedUser"
            label="用户"
            :items="[{ title: '演示运营', value: 'demo-operator' }, { title: '演示财务', value: 'demo-finance' }, { title: '演示员工', value: 'demo-employee' }]"
          /><VBtn
            color="primary"
            @click="changeEffectiveUser"
          >
            查看有效权限
          </VBtn>
        </div><VTable>
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
                <VChip
                  size="small"
                  :color="item.allowed ? 'success' : 'error'"
                >
                  {{ item.allowed ? '允许' : '拒绝' }}
                </VChip>
              </td><td>{{ item.sources.join('；') || '—' }}</td><td>{{ item.deniedBy.join('；') || '—' }}</td>
            </tr>
          </tbody>
        </VTable>
      </VCardText>
    </VCard>

    <VCard
      v-else-if="props.pageId === 'SYS22'"
      :title="title"
    >
      <VCardText>
        <VAlert
          type="warning"
          variant="tonal"
          class="mb-4"
        >
          敏感权限保存前必须填写另一位管理员的确认身份；拒绝优先。
        </VAlert><VTable>
          <thead><tr><th>角色</th><th>权限点</th><th>效果</th><th>敏感</th></tr></thead><tbody>
            <tr
              v-for="item in matrix.slice(0, 24)"
              :key="`${item.roleId}-${item.permissionKey}`"
            >
              <td>{{ item.roleId }}</td><td>{{ item.permissionKey }}</td><td>
                <AppSelect
                  v-model="item.effect"
                  :items="['allow', 'inherit', 'deny', 'none']"
                  density="compact"
                  hide-details
                />
              </td><td>{{ item.sensitive ? '是' : '否' }}</td>
            </tr>
          </tbody>
        </VTable><div class="d-flex gap-4 align-center mt-4">
          <AppTextField
            v-model="confirmer"
            label="另一位管理员确认人"
          /><VBtn
            color="primary"
            @click="saveMatrix"
          >
            保存矩阵
          </VBtn>
        </div>
      </VCardText>
    </VCard>

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
