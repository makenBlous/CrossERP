<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { calculateGapDPayrollRun, createGapDTool, fetchGapDAutonomyPolicies, fetchGapDPayrollRules, fetchGapDPayrollRun, fetchGapDRecords, fetchGapDTools, importGapDMcp, saveGapDAutonomy, setGapDAiMode } from '@/api/gap-d'
import { findPageById } from '@/config/pages'
import DetailPage from '@/components/biz/DetailPage.vue'
import FormPage from '@/components/biz/FormPage.vue'
import ListPage, { type ListColumn } from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useAiModeStore } from '@/stores/ai-mode'
import type { AgentAutonomyLevel } from '@/types/foundation'
import type { GapDPageId, GapDPayrollRule, GapDRecord } from '@/types/gap-d'

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
const selectedRecord = computed(() => records.value[0])
const page = computed(() => findPageById(props.pageId))
const title = computed(() => page.value?.name['zh-CN'] ?? props.pageId)
const subtitle = computed(() => page.value?.purpose['zh-CN'] ?? '批次 D 静态演示页面')
const isAgentPage = computed(() => props.pageId.startsWith('G'))
const detailPage = computed(() => ['HR03', 'HR08', 'AM03', 'G24'].includes(props.pageId))
const formPage = computed(() => ['G25', 'HR06', 'HR10', 'HR11', 'AM04'].includes(props.pageId))

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
  message.value = ''
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
  if (props.pageId === 'HR02')
    router.push(`/hr/employees/${row.id}`)
  else if (props.pageId === 'HR07')
    router.push('/hr/payroll/payroll-2026-11')
  else if (props.pageId === 'G24')
    router.push(`/agent/tools/${row.id}`)
}

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
          <VBtn
            size="small"
            variant="text"
            :loading="saving"
            @click="savePolicy(item.id)"
          >
            保存
          </VBtn>
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
          /><VBtn
            :loading="saving"
            @click="calculatePayroll"
          >
            发起算薪
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
          工资字段仅人事、获授权财务和员工本人可见。规则版本和每个数字均来自确定性计算。
        </VAlert>
        <VCard
          v-if="payrollRun"
          title="工资明细"
        >
          <VTable>
            <thead><tr><th>员工</th><th>应发</th><th>社保/公积金</th><th>累计应纳税所得额</th><th>本月个税</th><th>实发</th></tr></thead><tbody>
              <tr
                v-for="row in payrollRun.payslips"
                :key="row.id"
              >
                <td>{{ row.employeeName }}</td><td>
                  <MoneyText
                    :amount="row.grossCents / 100"
                    currency="CNY"
                  />
                </td><td>
                  <MoneyText
                    :amount="(row.socialPersonalCents + row.housingFundPersonalCents) / 100"
                    currency="CNY"
                  />
                </td><td>
                  <MoneyText
                    :amount="row.taxableCumulativeCents / 100"
                    currency="CNY"
                  />
                </td><td>
                  <MoneyText
                    :amount="row.taxCents / 100"
                    currency="CNY"
                  />
                </td><td>
                  <MoneyText
                    :amount="row.netCents / 100"
                    currency="CNY"
                  />
                </td>
              </tr>
            </tbody>
          </VTable>
          <VCardActions v-if="props.pageId === 'HR09'">
            <VBtn
              :disabled="!payrollRun"
              @click="message = 'HR 复核已记录，下一步进入财务审批。'"
            >
              复核通过并提交审批
            </VBtn>
          </VCardActions>
        </VCard>
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
      >
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

    <template v-else-if="props.pageId === 'G26'">
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
          /><VBtn
            size="small"
            variant="text"
            @click="importMcp(item.id)"
          >
            导入工具
          </VBtn>
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
      </DetailPage>
    </template>

    <template v-else-if="formPage">
      <FormPage
        :title="title"
        :subtitle="subtitle"
        @save="message = '已保存演示草稿，后续流程将进入审批。'"
        @cancel="router.back()"
      >
        <AppTextField
          label="标题"
          model-value="演示草稿"
        /><AppTextarea
          class="mt-4"
          label="说明"
          model-value="人工填写路径；AI 关闭时仍可提交。"
        /><template #aside>
          <VAlert
            type="info"
            variant="tonal"
          >
            本页面保留完整人工路径。涉及薪资的计算由服务层按规则完成。
          </VAlert>
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
        <template #item.status="{ item }">
          <StatusChip
            domain="generic"
            :value="String(item.status)"
          />
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
  </div>
</template>
