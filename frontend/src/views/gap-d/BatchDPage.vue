<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { currentActor } from '@/api/mock-client'
import { approveLeave, approvePayroll, calculateGapDPayrollRun, checkoutAsset, configureGapDToolSettings, createGapDTool, editContract, fetchGapDAutonomyPolicies, fetchGapDPayrollRules, fetchGapDPayrollRun, fetchGapDRecords, fetchGapDTools, importGapDMcp, publishPayslips, registerGapDMcp, registerMockImport, returnAsset, reviewPayroll, saveDeduction, saveGapDAutonomy, saveGapDOperation, savePayrollRule, setGapDAiMode, setGapDToolEnabled, submitLeave, testGapDToolCall, transitionEmployeeStatus, uploadGapDInbox } from '@/api/gap-d'
import { findPageById } from '@/config/pages'
import KpiCard from '@/components/KpiCard.vue'
import DetailPage from '@/components/biz/DetailPage.vue'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import FormPage from '@/components/biz/FormPage.vue'
import ListPage, { type ListColumn } from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import RecordDrawer from '@/components/biz/RecordDrawer.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useAiModeStore } from '@/stores/ai-mode'
import { effectivePermission, roleSubject } from '@/utils/permission-engine'
import type { AgentAutonomyLevel } from '@/types/foundation'
import type { GapDPageId, GapDPayrollRule, GapDPayslip, GapDRecord } from '@/types/gap-d'

const props = defineProps<{ pageId: GapDPageId }>()
const route = useRoute()
const router = useRouter()
const routeParams = route.params as Record<string, string | undefined>
const aiMode = useAiModeStore()
const loading = ref(false)
const saving = ref(false)
const message = ref('')
const records = ref<GapDRecord[]>([])
const policies = ref<Awaited<ReturnType<typeof fetchGapDAutonomyPolicies>>>([])
const tools = ref<Awaited<ReturnType<typeof fetchGapDTools>>>([])
const payrollRules = ref<GapDPayrollRule[]>([])
const payrollRun = ref<Awaited<ReturnType<typeof fetchGapDPayrollRun>>>(null)
const period = ref('2026-11')
const selectedLevel = ref<Record<string, AgentAutonomyLevel>>({})
const toolName = ref('自定义 HTTP 工具')
const toolEndpoint = ref('https://example.test/read-only')
const toolFrequency = ref(20)
const toolSecret = ref(false)
const inboxFile = ref<File | null>(null)
const recordDrawerOpen = ref(false)
const drawerRecord = ref<GapDRecord | null>(null)
const operationDrawerOpen = ref(false)
const toolDrawerOpen = ref(false)
const operationTitle = ref('')
const operationLabel = ref('')
const operationDraft = ref({ title: '', detail: '' })
const formDraft = ref({ title: '', detail: '' })
const payslipDrawerOpen = ref(false)
const selectedPayslip = ref<GapDPayslip | null>(null)
const reviewDrawerOpen = ref(false)
const reviewReason = ref('')
const ruleDrawerOpen = ref(false)
const editingRule = ref<GapDPayrollRule | null>(null)
const ruleDraft = ref({ city: '', effectiveFrom: '', pensionRate: 0, medicalRate: 0, unemploymentRate: 0, housingFundRate: 0, baseMinCents: 0, baseMaxCents: 0 })
const leaveDraft = ref({ startDate: '2026-11-20', endDate: '2026-11-21', reason: '' })
const importFileName = ref('')
const importRowCount = ref(1)
const mcpName = ref('本地 MCP 演示服务器')
const mcpEndpoint = ref('stdio://crosserp-demo')
const operationPages = new Set<GapDPageId>(['HR01', 'HR04', 'HR05', 'G21', 'G22', 'G23', 'AM01', 'AM02', 'AM05'])
const selectedRecord = computed(() => records.value[0])
const page = computed(() => findPageById(props.pageId))
const title = computed(() => page.value?.name['zh-CN'] ?? props.pageId)
const subtitle = computed(() => page.value?.purpose['zh-CN'] ?? '批次 D 静态演示页面')
const isAgentPage = computed(() => props.pageId.startsWith('G'))
const detailPage = computed(() => ['HR03', 'HR08', 'AM03', 'G24'].includes(props.pageId))
const formPage = computed(() => ['G25', 'HR06', 'HR10', 'HR11', 'AM04'].includes(props.pageId))
const canAddOperation = computed(() => operationPages.has(props.pageId))

function canPermission(permissionKey: string) {
  const actor = currentActor()

  return effectivePermission(roleSubject(actor.role, actor.userId), permissionKey).allowed
}

const canSubmitLeave = computed(() => canPermission('leave_application:create'))
const canApproveLeave = computed(() => canPermission('leave_application:approve_manager') || canPermission('leave_application:approve_hr'))
const canCalculatePayroll = computed(() => canPermission('payroll_run:calculate'))
const canReviewPayroll = computed(() => canPermission('salary_slip:review'))
const canApprovePayroll = computed(() => canPermission('salary_slip:approve'))
const canPublishPayslips = computed(() => canPermission('salary_slip:write'))

const payrollColumns: ListColumn[] = [
  { key: 'employeeName', title: '员工' },
  { key: 'grossCents', title: '应发' },
  { key: 'socialPersonalCents', title: '社保个人' },
  { key: 'housingFundPersonalCents', title: '公积金个人' },
  { key: 'taxableCumulativeCents', title: '累计应纳税所得额' },
  { key: 'taxCents', title: '本月个税' },
  { key: 'netCents', title: '实发' },
  { key: 'status', title: '状态' },
]

const columns = computed<ListColumn[]>(() => {
  if (props.pageId === 'G18')
    return [{ key: 'title', title: '动作' }, { key: 'status', title: '当前等级' }, { key: 'detail', title: '硬上限说明' }]
  if (props.pageId === 'G24' || props.pageId === 'G26')
    return [{ key: 'title', title: '名称' }, { key: 'status', title: '状态' }, { key: 'detail', title: '配置摘要' }]
  if (props.pageId === 'HR02')
    return [{ key: 'title', title: '姓名' }, { key: 'department', title: '部门' }, { key: 'status', title: '状态' }, { key: 'salaryCents', title: '薪资字段' }]
  if (props.pageId === 'HR12')
    return [{ key: 'title', title: '期间' }, { key: 'owner', title: '员工' }, { key: 'amount', title: '实发' }, { key: 'status', title: '状态' }]

  return [{ key: 'title', title: '记录' }, { key: 'status', title: '状态' }, { key: 'owner', title: '负责人' }, { key: 'detail', title: '说明' }]
})

async function load() {
  loading.value = true
  try {
    records.value = await fetchGapDRecords(props.pageId)
    if (props.pageId === 'G18') {
      policies.value = await fetchGapDAutonomyPolicies()
      for (const item of policies.value)
        selectedLevel.value[item.id] = item.level
    }
    if (props.pageId === 'G04' || props.pageId === 'G24' || props.pageId === 'G25')
      tools.value = await fetchGapDTools()
    if (props.pageId === 'HR07' || props.pageId === 'HR10')
      payrollRules.value = await fetchGapDPayrollRules()
    if (props.pageId === 'HR08' || props.pageId === 'HR09')
      payrollRun.value = await fetchGapDPayrollRun(String(routeParams.id ?? 'payroll-2026-11'))
  }
  catch (error) {
    message.value = error instanceof Error ? error.message : '加载失败'
  }
  finally { loading.value = false }
}

async function setMode(mode: 'normal' | 'degraded' | 'off') {
  saving.value = true
  try {
    const result = await setGapDAiMode(mode, mode === 'off' ? '人工路径演示' : '批次 D 控制台操作')

    aiMode.setMode(result.mode, result.changedBy, result.reason)
    message.value = `AI 状态已切换为${mode === 'normal' ? '正常' : mode === 'degraded' ? '降级' : '关闭'}`
  }
  catch (error) { message.value = error instanceof Error ? error.message : '切换失败' }
  finally { saving.value = false }
}

async function savePolicy(id: string) {
  saving.value = true
  try {
    await saveGapDAutonomy(id, selectedLevel.value[id])
    message.value = '自治等级已保存；涉及凭证、付款、薪资的 L3 会被硬上限拦截。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '保存失败' }
  finally { saving.value = false }
}

async function createTool() {
  saving.value = true
  try {
    await createGapDTool({ name: toolName.value, kind: 'http', endpoint: toolEndpoint.value, frequencyLimit: toolFrequency.value, secretConfigured: toolSecret.value })
    toolDrawerOpen.value = false
    message.value = '工具已登记，默认停用且只读；密钥只保存“已配置”状态。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '保存工具失败' }
  finally { saving.value = false }
}

async function importMcp(id: string) {
  try {
    await importGapDMcp(id)
    message.value = 'MCP 工具已导入，默认停用。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '导入失败' }
}

async function uploadInbox() {
  if (!inboxFile.value)
    return
  try {
    await uploadGapDInbox(inboxFile.value.name)
    message.value = '票据已收件，等待确定性字段抽取；AI 关闭时仍可人工归档。'
    inboxFile.value = null
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '上传失败' }
}

async function toggleTool(id: string, enabled: boolean) {
  try {
    await setGapDToolEnabled(id, enabled)
    message.value = enabled ? '工具已启用；联网工具仍是只读且必须带出处。' : '工具已停用。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '更新工具失败' }
}

async function configureTool(id: string) {
  try {
    await configureGapDToolSettings(id, { secretConfigured: true, frequencyLimit: toolFrequency.value })
    message.value = '密钥已配置（仅保存状态），频率上限已更新。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '配置工具失败' }
}

async function testTool(id: string) {
  try {
    const result = await testGapDToolCall(id)

    message.value = `测试调用成功：${result.citation}`
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '测试调用失败' }
}

async function registerMcp() {
  try {
    await registerGapDMcp({ name: mcpName.value, transport: 'stdio', endpoint: mcpEndpoint.value, discoveredTools: ['get_demo_stock'] })
    message.value = 'MCP 服务器已登记，导入工具默认停用。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '登记 MCP 服务器失败' }
}

async function calculatePayroll() {
  saving.value = true
  try {
    const result = await calculateGapDPayrollRun(period.value)

    payrollRun.value = result
    message.value = `${period.value} 算薪完成，${result.employeeCount} 人进入 HR 复核。`
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '算薪失败' }
  finally { saving.value = false }
}

function openRow(row: GapDRecord) {
  if (props.pageId === 'HR02') {
    router.push(`/hr/employees/${row.id}`)
  }
  else if (props.pageId === 'HR07') {
    router.push('/hr/payroll/payroll-2026-11')
  }
  else if (props.pageId === 'G04' || props.pageId === 'G24') {
    router.push(`/agent/tools/${row.id}`)
  }
  else {
    drawerRecord.value = row
    recordDrawerOpen.value = true
  }
}

function openOperation() {
  operationTitle.value = title.value
  operationLabel.value = props.pageId === 'HR01' ? '部门名称' : props.pageId === 'HR05' ? '考勤说明' : '标题'
  operationDraft.value = { title: '', detail: '' }
  operationDrawerOpen.value = true
}

async function saveOperation() {
  const titleText = operationDraft.value.title.trim()
  if (!titleText)
    return
  try {
    await saveGapDOperation(props.pageId, { title: titleText, detail: operationDraft.value.detail })
    operationDrawerOpen.value = false
    message.value = '人工记录已保存并写入审计；后续状态流转仍需按权限处理。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '保存记录失败' }
}

async function transitionEmployee() {
  try {
    await transitionEmployeeStatus('demo-employee', '离职')
    message.value = '员工已转为离职状态并写入审计。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '状态流转失败' }
}

async function importAttendance() {
  try {
    await registerMockImport('attendance', importFileName.value || 'attendance-demo.csv', importRowCount.value)
    message.value = '考勤模拟导入已登记（不保存真实文件），审计记录已写入。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '登记考勤导入失败' }
}

async function editSelectedContract() {
  const record = drawerRecord.value ?? selectedRecord.value
  if (!record)
    return
  try {
    await editContract(record.id, { status: '已终止' })
    message.value = '合同状态已保存并写入审计。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '编辑合同失败' }
}

async function checkoutSelectedAsset() {
  const record = drawerRecord.value ?? selectedRecord.value
  if (!record)
    return
  try {
    await checkoutAsset(record.id, 'demo-employee')
    drawerRecord.value = { ...record, status: '已领用', owner: 'demo-employee' }
    message.value = '资产已领用，库存/持有人由模拟服务更新。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '资产领用失败' }
}

async function returnSelectedAsset() {
  const record = drawerRecord.value ?? selectedRecord.value
  if (!record)
    return
  try {
    await returnAsset(record.id)
    drawerRecord.value = { ...record, status: '可领用', owner: undefined }
    message.value = '资产已归还并写入审计，现可再次领用。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '资产归还失败' }
}

async function approveSelectedLeave() {
  const request = records.value[0]
  if (!request)
    return
  try {
    await approveLeave(request.id)
    message.value = '请假审批状态已推进，不能跳过主管/人事顺序。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '请假审批失败' }
}

async function approveCurrentPayroll() {
  if (!payrollRun.value)
    return
  try {
    await approvePayroll(payrollRun.value.id)
    message.value = '财务审批已完成，薪资批次进入已出凭证。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '财务审批失败' }
}

async function publishCurrentPayslips() {
  if (!payrollRun.value)
    return
  try {
    await publishPayslips(payrollRun.value.id)
    message.value = '工资条已发布，员工只能通过本人范围查看。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '工资条发布失败' }
}

async function saveFormDraft() {
  try {
    if (props.pageId === 'HR06') {
      await submitLeave({ startDate: leaveDraft.value.startDate, endDate: leaveDraft.value.endDate, reason: leaveDraft.value.reason || formDraft.value.detail || formDraft.value.title })
      message.value = '请假申请已提交，当前状态为待主管审批。'
    }
    else if (props.pageId === 'HR11') {
      await saveDeduction({ employeeId: 'demo-employee', category: formDraft.value.title || '子女教育', monthlyCents: 100000, effectiveFrom: '2026-01-01' })
      message.value = '专项附加扣除草稿已保存并写入审计。'
    }
    else if (props.pageId === 'HR10') {
      await savePayrollRule({ city: ruleDraft.value.city || '上海', effectiveFrom: ruleDraft.value.effectiveFrom || '2026-01-01', pensionRate: ruleDraft.value.pensionRate, medicalRate: ruleDraft.value.medicalRate, unemploymentRate: ruleDraft.value.unemploymentRate, housingFundRate: ruleDraft.value.housingFundRate, baseMinCents: ruleDraft.value.baseMinCents, baseMaxCents: ruleDraft.value.baseMaxCents })
      message.value = '规则草稿已保存，核实前不会用于生产算薪。'
    }
    else {
      if (!formDraft.value.title.trim())
        return
      await saveGapDOperation(props.pageId, formDraft.value)
      message.value = `${title.value}草稿已保存并写入审计，后续流程仍需人工审批。`
    }
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '保存失败' }
}

function openPayslip(row: GapDPayslip) {
  selectedPayslip.value = row
  payslipDrawerOpen.value = true
}

function openReview() {
  reviewReason.value = ''
  reviewDrawerOpen.value = true
}

async function submitReview() {
  if (!reviewReason.value.trim() || !payrollRun.value)
    return
  try {
    await reviewPayroll(payrollRun.value.id, reviewReason.value)
    reviewDrawerOpen.value = false
    message.value = '薪资复核已提交并写入审计，下一步进入财务审批。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '薪资复核失败' }
}

function openRule(rule?: GapDPayrollRule) {
  editingRule.value = rule ?? null
  ruleDraft.value = rule
    ? { city: rule.city, effectiveFrom: rule.effectiveFrom, pensionRate: rule.pensionRate, medicalRate: rule.medicalRate, unemploymentRate: rule.unemploymentRate, housingFundRate: rule.housingFundRate, baseMinCents: rule.baseMinCents, baseMaxCents: rule.baseMaxCents }
    : { city: '', effectiveFrom: '', pensionRate: 0, medicalRate: 0, unemploymentRate: 0, housingFundRate: 0, baseMinCents: 0, baseMaxCents: 0 }
  ruleDrawerOpen.value = true
}

async function saveRule() {
  if (!ruleDraft.value.city || !ruleDraft.value.effectiveFrom)
    return

  const rule: GapDPayrollRule = { id: editingRule.value?.id ?? `rule-${Date.now()}`, ...ruleDraft.value, verified: false }

  try {
    await savePayrollRule(rule)
    ruleDrawerOpen.value = false
    message.value = '规则草稿已保存，核实前不会用于生产算薪。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '保存规则失败' }
}

const payrollRows = computed(() => payrollRun.value?.payslips ?? [])
const trustScore = computed(() => String(records.value.find(item => item.score)?.score ?? '—'))

function amount(row: GapDRecord) {
  return Number(row.amount ?? 0)
}

function currency(row: GapDRecord) {
  return (row.currency ?? 'CNY') as 'CNY'
}

onMounted(load)
</script>

<template>
  <div>
    <VAlert
      v-if="isAgentPage && aiMode.mode === 'off'"
      type="info"
      variant="tonal"
      class="mb-4"
    >
      AI 已关闭，AI 区隐藏；人工路径仍可继续。
    </VAlert>
    <VAlert
      v-else-if="isAgentPage && aiMode.mode === 'degraded'"
      type="warning"
      variant="tonal"
      class="mb-4"
    >
      AI 降级：仅提供只读提示，L3 动作已暂停。
    </VAlert>
    <VAlert
      v-if="message"
      type="success"
      variant="tonal"
      closable
      class="mb-4"
      @click:close="message = ''"
    >
      {{ message }}
    </VAlert>

    <template v-if="props.pageId === 'G19'">
      <DetailPage
        :title="title"
        :subtitle="subtitle"
      >
        <VCard :title="`当前状态：${aiMode.mode === 'normal' ? '正常' : aiMode.mode === 'degraded' ? '降级' : '关闭'}`">
          <VCardText>
            <p class="text-body-2">
              切换会写入操作日志；AI 无法自行修改等级或开关。
            </p>
            <PermissionGate action="update">
              <div class="d-flex flex-wrap gap-3">
                <VBtn
                  color="success"
                  :loading="saving"
                  @click="setMode('normal')"
                >
                  正常
                </VBtn>
                <VBtn
                  color="warning"
                  variant="tonal"
                  :loading="saving"
                  @click="setMode('degraded')"
                >
                  降级
                </VBtn>
                <VBtn
                  color="secondary"
                  variant="tonal"
                  :loading="saving"
                  @click="setMode('off')"
                >
                  关闭
                </VBtn>
              </div>
            </PermissionGate>
          </VCardText>
        </VCard>
      </DetailPage>
    </template>

    <template v-else-if="props.pageId === 'G18'">
      <ListPage
        storage-key="gapd-autonomy"
        :title="title"
        :subtitle="subtitle"
        :items="records"
        :columns="columns"
      >
        <template #item.status="{ item }">
          <VSelect
            v-model="selectedLevel[item.id]"
            :items="['L0', 'L1', 'L2', 'L3']"
            density="compact"
            hide-details
            style="max-inline-size: 100px"
            :disabled="item.status === 'L2' && item.title.includes('voucher')"
          />
          <PermissionGate action="update">
            <VBtn
              size="small"
              variant="text"
              :loading="saving"
              @click="savePolicy(item.id)"
            >
              保存
            </VBtn>
          </PermissionGate>
        </template>
      </ListPage>
    </template>

    <template v-else-if="props.pageId === 'G25'">
      <FormPage
        :title="title"
        :subtitle="subtitle"
        :saving="saving"
        @save="createTool"
        @cancel="router.back()"
      >
        <VRow>
          <VCol cols="12">
            <AppTextField
              v-model="toolName"
              label="工具名称"
            />
          </VCol>
          <VCol cols="12">
            <AppTextField
              v-model="toolEndpoint"
              label="只读 HTTP 地址"
            />
          </VCol>
          <VCol
            cols="12"
            md="6"
          >
            <AppTextField
              v-model.number="toolFrequency"
              type="number"
              label="频率上限 / 日"
            />
          </VCol>
          <VCol
            cols="12"
            md="6"
          >
            <VSwitch
              v-model="toolSecret"
              label="模拟配置密钥（只显示已配置）"
            />
          </VCol>
        </VRow>
        <template #aside>
          <VAlert
            type="info"
            variant="tonal"
          >
            新工具默认停用、只读，联网结果必须带出处且不能直接触发起草。
          </VAlert>
        </template>
      </FormPage>
    </template>

    <template v-else-if="props.pageId === 'HR07'">
      <div class="d-flex flex-wrap justify-space-between align-center gap-3 mb-6">
        <div>
          <h4 class="text-h4">
            {{ title }}
          </h4><p class="mb-0">
            {{ subtitle }}
          </p>
        </div><div class="d-flex gap-3">
          <AppTextField
            v-model="period"
            type="month"
            label="算薪期间"
          />
          <div>
            <VBtn
              :loading="saving"
              :disabled="!canCalculatePayroll"
              @click="calculatePayroll"
            >
              发起算薪
            </VBtn>
          </div>
          <VBtn
            v-if="payrollRun?.status === '待审批'"
            variant="tonal"
            :disabled="!canApprovePayroll"
            @click="approveCurrentPayroll"
          >
            财务审批
          </VBtn>
          <VBtn
            v-if="payrollRun?.status === '已出凭证' && !payrollRun.publishedAt"
            variant="tonal"
            :disabled="!canPublishPayslips"
            @click="publishCurrentPayslips"
          >
            发布工资条
          </VBtn>
        </div>
      </div>
      <VAlert
        type="warning"
        variant="tonal"
        class="mb-4"
      >
        模拟规则，费率待会计/HR 核实，不代表已具备全国合规算税算社保能力。
      </VAlert>
      <ListPage
        storage-key="gapd-payroll"
        title="薪资批次"
        :items="payrollRun ? [{ id: payrollRun.id, title: payrollRun.period, status: payrollRun.status, owner: `${payrollRun.employeeCount} 人`, detail: '确定性计算完成', updatedAt: payrollRun.createdAt }] : []"
        :columns="columns"
        @open="openRow"
      />
    </template>

    <template v-else-if="props.pageId === 'HR08' || props.pageId === 'HR09'">
      <DetailPage
        :title="title"
        :subtitle="subtitle"
        status="待复核"
        domain="generic"
      >
        <VAlert
          type="warning"
          variant="tonal"
          class="mb-4"
        >
          员工档案薪资字段仅人事和本人可见；工资批次明细需单独的算薪审批权限。规则版本和每个数字均来自确定性计算。
        </VAlert>
        <ListPage
          v-if="payrollRun"
          storage-key="gapd-payslips"
          title="工资明细"
          subtitle="点击员工查看规则版本与确定性计算明细"
          :items="payrollRows"
          :columns="payrollColumns"
          @open="openPayslip"
        >
          <template #item.grossCents="{ item }">
            <MoneyText
              :amount="item.grossCents"
              minor
              currency="CNY"
            />
          </template>
          <template #item.socialPersonalCents="{ item }">
            <MoneyText
              :amount="item.socialPersonalCents"
              minor
              currency="CNY"
            />
          </template>
          <template #item.housingFundPersonalCents="{ item }">
            <MoneyText
              :amount="item.housingFundPersonalCents"
              minor
              currency="CNY"
            />
          </template>
          <template #item.taxableCumulativeCents="{ item }">
            <MoneyText
              :amount="item.taxableCumulativeCents"
              minor
              currency="CNY"
            />
          </template>
          <template #item.taxCents="{ item }">
            <MoneyText
              :amount="item.taxCents"
              minor
              currency="CNY"
            />
          </template>
          <template #item.netCents="{ item }">
            <MoneyText
              :amount="item.netCents"
              minor
              currency="CNY"
            />
          </template>
          <template #item.status="{ item }">
            <StatusChip
              domain="generic"
              :value="item.status"
            />
          </template>
        </ListPage>
        <VCardActions v-if="props.pageId === 'HR09'">
          <div>
            <VBtn
              :disabled="!payrollRun || !canReviewPayroll"
              @click="openReview"
            >
              填写复核原因并提交审批
            </VBtn>
          </div>
          <VBtn
            v-if="payrollRun?.status === '待审批'"
            variant="tonal"
            :disabled="!canApprovePayroll"
            @click="approveCurrentPayroll"
          >
            财务审批
          </VBtn>
          <VBtn
            v-if="payrollRun?.status === '已出凭证' && !payrollRun.publishedAt"
            variant="tonal"
            :disabled="!canPublishPayslips"
            @click="publishCurrentPayslips"
          >
            发布工资条
          </VBtn>
        </VCardActions>
        <VAlert
          v-else
          type="info"
          variant="tonal"
        >
          请先在薪资批次页发起算薪。
        </VAlert>
      </DetailPage>
    </template>

    <template v-else-if="props.pageId === 'HR10'">
      <ListPage
        storage-key="gapd-payroll-rules"
        :title="title"
        :subtitle="subtitle"
        :items="payrollRules"
        :columns="[{ key: 'city', title: '城市' }, { key: 'effectiveFrom', title: '生效日' }, { key: 'pensionRate', title: '养老个人比例' }, { key: 'housingFundRate', title: '公积金个人比例' }, { key: 'verified', title: '核实状态' }]"
        @open="openRule"
      >
        <template #widgets>
          <div class="d-flex justify-end mb-4">
            <PermissionGate action="create">
              <VBtn @click="openRule">
                新增规则版本
              </VBtn>
            </PermissionGate>
          </div>
        </template>
        <template #item.pensionRate="{ item }">
          {{ (item.pensionRate * 100).toFixed(2) }}%
        </template><template #item.housingFundRate="{ item }">
          {{ (item.housingFundRate * 100).toFixed(2) }}%
        </template><template #item.verified="{ item }">
          <StatusChip
            domain="generic"
            :value="item.verified ? '已核实' : '待核实'"
          />
        </template>
      </ListPage>
      <VAlert
        type="warning"
        variant="tonal"
        class="mt-4"
      >
        模拟规则，费率待会计/HR 核实，不代表已具备全国合规算税算社保能力；费率保存在规则配置中。
      </VAlert>
    </template>

    <template v-else-if="props.pageId === 'G22'">
      <VRow class="mb-6">
        <VCol
          cols="12"
          md="4"
        >
          <KpiCard
            title="当前采纳率"
            :value="trustScore"
            icon="tabler-target"
            color="success"
            hint="来自最近一轮离线评测"
          />
        </VCol>
        <VCol
          cols="12"
          md="4"
        >
          <KpiCard
            title="基线"
            value="90%"
            icon="tabler-chart-line"
            color="info"
            hint="评测基线，不代表生产承诺"
          />
        </VCol>
        <VCol
          cols="12"
          md="4"
        >
          <KpiCard
            title="降级次数"
            value="2"
            icon="tabler-alert-triangle"
            color="warning"
            hint="可从审计记录追溯"
          />
        </VCol>
      </VRow>
      <ListPage
        storage-key="gapd-trust"
        :title="title"
        :subtitle="subtitle"
        :items="records"
        :columns="columns"
        @open="openRow"
      >
        <template #item.status="{ item }">
          <StatusChip
            domain="generic"
            :value="String(item.status)"
          />
        </template>
      </ListPage>
    </template>

    <template v-else-if="props.pageId === 'G20'">
      <div class="d-flex flex-wrap justify-space-between align-center gap-3 mb-6">
        <div>
          <h4 class="text-h4">
            {{ title }}
          </h4>
          <p class="mb-0">
            {{ subtitle }}
          </p>
        </div>
        <div class="d-flex gap-3 align-center">
          <VFileInput
            v-model="inboxFile"
            label="上传发票/报价单"
            accept=".pdf,.jpg,.png,.csv"
            hide-details
          />
          <VBtn
            :disabled="!inboxFile"
            @click="uploadInbox"
          >
            收件
          </VBtn>
        </div>
      </div>
      <ListPage
        storage-key="gapd-inbox"
        :title="title"
        :subtitle="subtitle"
        :items="records"
        :columns="columns"
        :loading="loading"
      >
        <template #item.status="{ item }">
          <StatusChip
            domain="generic"
            :value="String(item.status)"
          />
        </template>
      </ListPage>
    </template>

    <template v-else-if="props.pageId === 'G26'">
      <VCard class="mb-4">
        <VCardText class="d-flex flex-wrap align-end gap-3">
          <AppTextField
            v-model="mcpName"
            label="MCP 服务器名称"
          />
          <AppTextField
            v-model="mcpEndpoint"
            label="连接地址"
          />
          <VBtn @click="registerMcp">
            登记服务器
          </VBtn>
        </VCardText>
      </VCard>
      <ListPage
        storage-key="gapd-mcp"
        :title="title"
        :subtitle="subtitle"
        :items="records"
        :columns="columns"
      >
        <template #item.status="{ item }">
          <StatusChip
            domain="generic"
            :value="String(item.status)"
          /><PermissionGate action="update">
            <VBtn
              size="small"
              variant="text"
              @click="importMcp(item.id)"
            >
              导入工具
            </VBtn>
          </PermissionGate>
        </template>
      </ListPage>
    </template>

    <template v-else-if="detailPage">
      <DetailPage
        :title="title"
        :subtitle="subtitle"
        :timeline="[{ at: '2026-11-10 08:00', title: '演示记录', detail: selectedRecord?.detail ?? '静态演示数据', actor: '系统' }]"
      >
        <VCard :title="selectedRecord?.title ?? title">
          <VCardText>
            <p>{{ selectedRecord?.detail ?? subtitle }}</p><MoneyText
              v-if="selectedRecord?.amount"
              :amount="amount(selectedRecord)"
              :currency="currency(selectedRecord)"
            />
          </VCardText>
        </VCard>
        <VCard
          v-if="props.pageId === 'G24' && selectedRecord"
          class="mt-4"
          title="工具配置"
        >
          <VCardText>
            <PermissionGate action="update">
              <VSwitch
                :model-value="selectedRecord.status === '已启用'"
                label="启用工具"
                @update:model-value="toggleTool(selectedRecord.id, Boolean($event))"
              />
            </PermissionGate>
            <VAlert
              type="info"
              variant="tonal"
            >
              密钥：{{ selectedRecord.secretConfigured ? '已配置' : '未配置' }}；读写类别：只读。
            </VAlert>
            <div class="d-flex flex-wrap gap-2 mt-3">
              <VBtn
                size="small"
                variant="tonal"
                @click="configureTool(selectedRecord.id)"
              >
                配置密钥与频率
              </VBtn>
              <VBtn
                size="small"
                variant="tonal"
                @click="testTool(selectedRecord.id)"
              >
                测试调用
              </VBtn>
            </div>
          </VCardText>
        </VCard>
      </DetailPage>
    </template>

    <template v-else-if="formPage">
      <FormPage
        :title="title"
        :subtitle="subtitle"
        :save-disabled="props.pageId === 'HR06' && !canSubmitLeave"
        @save="saveFormDraft"
        @cancel="router.back()"
      >
        <template v-if="props.pageId === 'HR06'">
          <VRow>
            <VCol cols="6">
              <AppTextField
                v-model="leaveDraft.startDate"
                label="开始日期"
                type="date"
              />
            </VCol>
            <VCol cols="6">
              <AppTextField
                v-model="leaveDraft.endDate"
                label="结束日期"
                type="date"
              />
            </VCol>
          </VRow>
          <AppTextarea
            v-model="leaveDraft.reason"
            class="mt-4"
            label="请假原因"
            rows="3"
          />
        </template>
        <AppTextField
          v-model="formDraft.title"
          label="标题"
          :placeholder="props.pageId === 'HR06' ? '年假申请' : '演示草稿'"
        /><AppTextarea
          v-model="formDraft.detail"
          class="mt-4"
          label="说明"
          placeholder="人工填写路径；AI 关闭时仍可提交。"
        /><template #aside>
          <VAlert
            type="info"
            variant="tonal"
          >
            本页面保留完整人工路径。涉及薪资的计算由服务层按规则完成。
          </VAlert>
          <VBtn
            v-if="props.pageId === 'HR06'"
            class="mt-3"
            variant="tonal"
            :disabled="!canApproveLeave"
            @click="approveSelectedLeave"
          >
            推进请假审批
          </VBtn>
          <VBtn
            v-if="props.pageId === 'HR06'"
            class="mt-3"
            variant="tonal"
            :disabled="!canSubmitLeave"
            @click="saveFormDraft"
          >
            提交请假
          </VBtn>
        </template>
      </FormPage>
    </template>

    <template v-else>
      <ListPage
        :storage-key="`gapd-${props.pageId}`"
        :title="title"
        :subtitle="subtitle"
        :items="records"
        :columns="columns"
        :loading="loading"
        @open="openRow"
      >
        <template #widgets>
          <div
            v-if="canAddOperation || props.pageId === 'G04'"
            class="d-flex flex-wrap justify-end align-end gap-3 mb-4"
          >
            <AppTextField
              v-if="props.pageId === 'HR05'"
              v-model="importFileName"
              label="模拟考勤文件名"
            />
            <AppTextField
              v-if="props.pageId === 'HR05'"
              v-model.number="importRowCount"
              type="number"
              label="行数"
            />
            <VBtn
              v-if="props.pageId === 'HR05'"
              variant="tonal"
              @click="importAttendance"
            >
              登记模拟导入
            </VBtn>
            <VBtn
              v-if="props.pageId === 'HR04'"
              variant="tonal"
              @click="transitionEmployee"
            >
              办理离职
            </VBtn>
            <VBtn
              v-if="props.pageId === 'G04'"
              variant="tonal"
              @click="toolDrawerOpen = true"
            >
              新增工具
            </VBtn>
            <PermissionGate action="create">
              <VBtn
                v-if="props.pageId !== 'HR05' && props.pageId !== 'HR04'"
                @click="openOperation"
              >
                {{ props.pageId === 'HR01' ? '新增部门' : '新增人工记录' }}
              </VBtn>
            </PermissionGate>
          </div>
        </template>
        <template #item.status="{ item }">
          <StatusChip
            domain="generic"
            :value="String(item.status)"
          />
          <template v-if="props.pageId === 'G04'">
            <VBtn
              size="small"
              variant="text"
              @click="toggleTool(item.id, item.status !== '已启用')"
            >
              {{ item.status === '已启用' ? '停用工具' : '启用工具' }}
            </VBtn>
            <VBtn
              size="small"
              variant="text"
              @click="configureTool(item.id)"
            >
              配置密钥与频率
            </VBtn>
            <VBtn
              size="small"
              variant="text"
              @click="testTool(item.id)"
            >
              测试调用
            </VBtn>
          </template>
        </template>
        <template #item.amount="{ item }">
          <MoneyText
            :amount="amount(item)"
            :currency="currency(item)"
          />
        </template>
        <template #item.salaryCents="{ item }">
          <span v-if="item.salaryCents != null"><MoneyText
            :amount="Number(item.salaryCents) / 100"
            currency="CNY"
          /></span><span
            v-else
            class="text-medium-emphasis"
          >无权查看</span>
        </template>
      </ListPage>
    </template>

    <RecordDrawer
      v-model="recordDrawerOpen"
      :title="drawerRecord?.title ?? title"
    >
      <template v-if="drawerRecord">
        <VList density="compact">
          <VListItem
            title="状态"
            :subtitle="drawerRecord.status"
          />
          <VListItem
            title="负责人"
            :subtitle="drawerRecord.owner ?? '未指定'"
          />
          <VListItem
            title="说明"
            :subtitle="drawerRecord.detail ?? '无'"
          />
          <VListItem
            title="更新时间"
            :subtitle="drawerRecord.updatedAt"
          />
        </VList>
        <VAlert
          type="info"
          variant="tonal"
          class="mt-4"
        >
          记录详情沿用 Vuexy 抽屉模式；需要写入的动作仍通过人工路径和权限校验完成。
        </VAlert>
        <div class="d-flex flex-wrap gap-2 mt-3">
          <VBtn
            v-if="props.pageId === 'AM01'"
            variant="tonal"
            @click="editSelectedContract"
          >
            编辑合同状态
          </VBtn>
          <VBtn
            v-if="props.pageId === 'AM02' || props.pageId === 'AM03'"
            variant="tonal"
            @click="checkoutSelectedAsset"
          >
            资产领用
          </VBtn>
          <VBtn
            v-if="props.pageId === 'AM02' || props.pageId === 'AM03'"
            variant="tonal"
            @click="returnSelectedAsset"
          >
            资产归还
          </VBtn>
        </div>
      </template>
    </RecordDrawer>

    <FormDrawer
      v-model="operationDrawerOpen"
      :title="operationTitle"
      @save="saveOperation"
    >
      <AppTextField
        v-model="operationDraft.title"
        :label="operationLabel"
        :rules="[requiredValidator]"
      />
      <AppTextarea
        v-model="operationDraft.detail"
        class="mt-4"
        label="说明"
        rows="4"
      />
    </FormDrawer>

    <FormDrawer
      v-model="toolDrawerOpen"
      title="新增工具"
      @save="createTool"
    >
      <AppTextField
        v-model="toolName"
        label="工具名称"
      />
      <AppTextField
        v-model="toolEndpoint"
        class="mt-4"
        label="只读 HTTP 地址"
      />
      <AppTextField
        v-model.number="toolFrequency"
        class="mt-4"
        type="number"
        label="频率上限 / 日"
      />
      <VSwitch
        v-model="toolSecret"
        class="mt-4"
        label="模拟配置密钥（只显示已配置）"
      />
      <VBtn
        class="mt-4"
        @click="createTool"
      >
        保存工具
      </VBtn>
    </FormDrawer>

    <RecordDrawer
      v-model="payslipDrawerOpen"
      title="工资计算明细"
    >
      <template v-if="selectedPayslip">
        <VList density="compact">
          <VListItem
            title="员工"
            :subtitle="selectedPayslip.employeeName"
          />
          <VListItem
            title="规则版本"
            :subtitle="selectedPayslip.ruleVersion"
          />
          <VListItem
            title="计算状态"
            :subtitle="selectedPayslip.status"
          />
        </VList>
        <VCard
          variant="tonal"
          class="mt-4"
        >
          <VCardText class="d-flex flex-column gap-2">
            <div class="d-flex justify-space-between">
              <span>应发</span><MoneyText
                :amount="selectedPayslip.grossCents"
                minor
                currency="CNY"
              />
            </div>
            <div class="d-flex justify-space-between">
              <span>社保/公积金个人</span><MoneyText
                :amount="selectedPayslip.socialPersonalCents + selectedPayslip.housingFundPersonalCents"
                minor
                currency="CNY"
              />
            </div>
            <div class="d-flex justify-space-between">
              <span>累计应纳税所得额</span><MoneyText
                :amount="selectedPayslip.taxableCumulativeCents"
                minor
                currency="CNY"
              />
            </div>
            <div class="d-flex justify-space-between">
              <span>本月个税</span><MoneyText
                :amount="selectedPayslip.taxCents"
                minor
                currency="CNY"
              />
            </div>
            <div class="d-flex justify-space-between font-weight-medium">
              <span>实发</span><MoneyText
                :amount="selectedPayslip.netCents"
                minor
                currency="CNY"
              />
            </div>
          </VCardText>
        </VCard>
      </template>
    </RecordDrawer>

    <FormDrawer
      v-model="reviewDrawerOpen"
      title="薪资复核"
      :save-disabled="!canReviewPayroll"
      @save="submitReview"
    >
      <VAlert
        type="warning"
        variant="tonal"
        class="mb-4"
      >
        调整或异常必须填写原因，提交后进入财务审批。
      </VAlert>
      <AppTextarea
        v-model="reviewReason"
        label="复核/调整原因"
        :rules="[requiredValidator]"
        rows="5"
      />
      <VBtn
        class="mt-3"
        :disabled="!canReviewPayroll"
        @click="submitReview"
      >
        提交复核
      </VBtn>
    </FormDrawer>

    <FormDrawer
      v-model="ruleDrawerOpen"
      :title="editingRule ? '编辑规则版本' : '新增规则版本'"
      @save="saveRule"
    >
      <AppTextField
        v-model="ruleDraft.city"
        label="城市"
        :rules="[requiredValidator]"
      />
      <AppTextField
        v-model="ruleDraft.effectiveFrom"
        class="mt-4"
        label="生效日"
        type="date"
        :rules="[requiredValidator]"
      />
      <VRow class="mt-2">
        <VCol cols="6">
          <AppTextField
            v-model.number="ruleDraft.pensionRate"
            label="养老个人比例"
            type="number"
          />
        </VCol>
        <VCol cols="6">
          <AppTextField
            v-model.number="ruleDraft.medicalRate"
            label="医疗个人比例"
            type="number"
          />
        </VCol>
        <VCol cols="6">
          <AppTextField
            v-model.number="ruleDraft.unemploymentRate"
            label="失业个人比例"
            type="number"
          />
        </VCol>
        <VCol cols="6">
          <AppTextField
            v-model.number="ruleDraft.housingFundRate"
            label="公积金个人比例"
            type="number"
          />
        </VCol>
        <VCol cols="6">
          <AppTextField
            v-model.number="ruleDraft.baseMinCents"
            label="基数下限（分）"
            type="number"
          />
        </VCol>
        <VCol cols="6">
          <AppTextField
            v-model.number="ruleDraft.baseMaxCents"
            label="基数上限（分）"
            type="number"
          />
        </VCol>
      </VRow>
    </FormDrawer>
  </div>
</template>
