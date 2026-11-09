<script setup lang="ts">
import { fetchGapBPage, submitGapBAction } from '@/api/gap-b'
import DetailPage from '@/components/biz/DetailPage.vue'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import FormPage from '@/components/biz/FormPage.vue'
import ListPage from '@/components/biz/ListPage.vue'
import LoadingState from '@/components/biz/LoadingState.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import RecordDrawer from '@/components/biz/RecordDrawer.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import KpiCard from '@/components/KpiCard.vue'
import { useAiModeStore } from '@/stores/ai-mode'
import type { GapBColumn, GapBKey, GapBPageData, GapBRow } from '@/types/gap-b'

const props = defineProps<{ pageKey: GapBKey }>()
const route = useRoute()
const router = useRouter()
const ai = useAiModeStore()
const data = ref<GapBPageData | null>(null)
const loading = ref(true)
const error = ref('')
const message = ref('')
const search = ref('')
const uploadFile = ref<File | null>(null)
const form = reactive({ source: '领星', fileName: '', subject: '', supplierCount: '2', amount: '120000', channel: '钉钉', account: '', endpoint: '', threshold: '50000', ledgerAccount: '', voucherType: '记', exportFormat: 'xlsx', erpnextSite: '', pushMode: '审批后可选推送' })
const wizardStep = ref(1)
const mapping = reactive<Record<string, string>>({ order_no: 'order_no', internal_sku: 'internal_sku', qty: 'qty', amount: 'amount' })
const imChannelEnabled = reactive<Record<string, boolean>>({ 飞书: true, 企业微信: false })
const createRfqOpen = ref(false)
const saving = ref(false)
const selectedImRow = ref<GapBRow | null>(null)
const imDrawerOpen = ref(false)
const actualQty = ref('317')

const chainItems = [
  { title: '客户 / 商机', detail: 'Acme Europe · 赢单' },
  { title: '销售订单', detail: 'SO-2026-001 · 客户和商机已关联' },
  { title: 'SKU → 采购 → 入库', detail: 'CN-1001 · PO-2026-001 · 华东 FBA' },
  { title: '物流运单 / 头程 / 出库', detail: 'FBA 批次 FM-2026-004 · 运单已关联' },
  { title: '凭证', detail: 'VCH-2026-018 · 可回溯来源单据' },
]

const id = computed(() => {
  const value = (route.params as Record<string, string | string[] | undefined>).id

  return Array.isArray(value) ? value[0] : value
})

const showAi = computed(() => ai.isEnabled)
const isDegraded = computed(() => ai.isReadOnly)
const isDetail = computed(() => Boolean(data.value?.detail))
const isForm = computed(() => data.value?.kind === 'form')

const scoreAverage = computed(() => {
  const values = (data.value?.rows ?? []).map(row => Number(row.score)).filter(value => Number.isFinite(value))

  return values.length ? (values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(1) : '—'
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await fetchGapBPage(props.pageKey, id.value)
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  }
  finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => [props.pageKey, id.value], load)

const displayColumns = computed<GapBColumn[]>(() => {
  const base = data.value?.columns ?? []
  if (['S09', 'S11', 'S13', 'I12', 'I13', 'I14', 'I15', 'INT01', 'INT02', 'INT05', 'W08', 'SYS19', 'SYS25'].includes(props.pageKey))
    return [...base, { key: 'actions', title: '操作' }]

  return base
})

function stringValue(row: GapBRow, key: string) {
  const value = row[key]

  return value == null ? '' : String(value)
}

function moneyValue(row: GapBRow, key: string) {
  const value = row[key]

  return typeof value === 'number' ? value : null
}

function detailPath(key: GapBKey, row: GapBRow) {
  const paths: Partial<Record<GapBKey, string>> = { S09: '/procurement/rfqs', S11: '/procurement/contracts', I14: '/inventory/transfers', I15: '/inventory/counts' }

  return paths[key] ? `${paths[key]}/${row.id}` : undefined
}

function openRow(row: GapBRow) {
  const path = detailPath(props.pageKey, row)
  if (path)
    router.push(path)
}

async function act(action: string, payload: Record<string, string | number | boolean> = {}) {
  message.value = ''
  try {
    message.value = await submitGapBAction(props.pageKey, action, payload)
    await load()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : '操作失败'
  }
}

async function saveRfq() {
  saving.value = true
  try {
    await act('create-rfq', { subject: form.subject || '新建补货询价', supplierCount: form.supplierCount, amount: form.amount })
    createRfqOpen.value = false
  }
  finally {
    saving.value = false
  }
}

async function saveForm() {
  saving.value = true
  try {
    if (props.pageKey === 'INT01') {
      if (wizardStep.value === 1) {
        if (!uploadFile.value) {
          message.value = '请先选择领星或赛狐导出文件。'

          return
        }
        await act('upload-import')
        wizardStep.value = 2

        return
      }
      if (wizardStep.value === 2) {
        await act('preview-import')
        wizardStep.value = 3

        return
      }
      await act('confirm-import')
      wizardStep.value = 4

      return
    }
    if (props.pageKey === 'SYS26') {
      await act('create-channel', { channel: form.channel })

      return
    }
    await act('save-settings', { endpoint: form.endpoint, threshold: form.threshold, ledgerAccount: form.ledgerAccount, voucherType: form.voucherType, exportFormat: form.exportFormat, erpnextSite: form.erpnextSite, pushMode: form.pushMode })
  }
  finally {
    saving.value = false
  }
}

async function confirmTransfer() {
  await act('confirm-transfer', { id: id.value || data.value?.detail?.id || '' })
}

async function submitCount() {
  await act('submit-count', { id: id.value || data.value?.detail?.id || '', actualQty: actualQty.value })
}

async function openIm(row: GapBRow) {
  selectedImRow.value = row
  imDrawerOpen.value = true
}

async function toggleChannel(row: GapBRow) {
  await act('toggle-channel', { id: row.id, enabled: !row.enabled })
}

async function testChannel(row?: GapBRow) {
  await act('test-channel', { id: row?.id ?? '', channel: row && typeof row.channel === 'string' ? row.channel : form.channel })
}

async function saveAttachment(value: File | File[] | null) {
  const file = Array.isArray(value) ? value[0] : value
  if (file)
    await act('save-attachment', { fileName: file.name })
}

function rowStatus(row: GapBRow) {
  const value = row.status

  return typeof value === 'string' ? value : ''
}
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
      v-if="message"
      type="success"
      variant="tonal"
      class="mb-4"
      data-test="gap-b-message"
    >
      {{ message }}
    </VAlert>
    <VAlert
      v-if="isDegraded"
      type="warning"
      variant="tonal"
      class="mb-4"
      data-test="ai-degraded"
    >
      AI 当前为降级模式，只提供只读建议；人工流程仍可继续。
    </VAlert>
    <VAlert
      v-if="data?.audit?.length"
      type="info"
      variant="tonal"
      class="mb-4"
      data-test="gap-b-audit"
    >
      最近审计：{{ data.audit[0].action }} · {{ data.audit[0].summary }}（{{ data.audit[0].actor }}）
    </VAlert>

    <template v-if="loading">
      <LoadingState />
    </template>

    <template v-else-if="data && isDetail && data.detail">
      <DetailPage
        :title="data.detail.title"
        :subtitle="data.detail.summary"
        domain="generic"
        :status="data.detail.status"
        :timeline="data.detail.steps.map(step => ({ id: step.id, at: step.status === 'done' ? '已完成' : '当前', title: step.title, detail: step.detail }))"
        :related="data.detail.related"
      >
        <template #actions>
          <PermissionGate
            v-if="props.pageKey === 'I14'"
            action="update"
          >
            <VBtn
              :disabled="data.detail.status === 'posted'"
              data-test="confirm-transfer"
              @click="confirmTransfer"
            >
              {{ data.detail.status === 'posted' ? '已确认调拨' : '确认调拨' }}
            </VBtn>
          </PermissionGate>
          <PermissionGate
            v-if="props.pageKey === 'I15'"
            action="approve"
          >
            <VBtn
              v-if="data.detail.status === 'submitted'"
              variant="tonal"
              color="success"
              data-test="approve-count"
              @click="act('approve-count', { id: data.detail.id })"
            >
              审批通过并过账
            </VBtn>
          </PermissionGate>
          <PermissionGate
            v-if="props.pageKey === 'I15'"
            action="update"
          >
            <VBtn
              :disabled="data.detail.status !== 'pending'"
              data-test="submit-count"
              @click="submitCount"
            >
              {{ data.detail.status === 'pending' ? '提交差异审批' : '已提交审批' }}
            </VBtn>
          </PermissionGate>
        </template>
        <VCard class="mb-6">
          <VCardText>
            <VRow>
              <VCol
                v-for="field in data.detail.fields"
                :key="field.label"
                cols="12"
                sm="6"
              >
                <div class="text-caption text-medium-emphasis">
                  {{ field.label }}
                </div>
                <div class="text-body-1 font-weight-medium">
                  {{ field.value }}
                </div>
              </VCol>
            </VRow>
          </VCardText>
        </VCard>
        <VCard
          v-if="props.pageKey === 'S12'"
          title="合同价格表与附件"
          class="mb-6"
        >
          <VTable density="compact">
            <thead><tr><th>SKU</th><th>含税单价</th><th>生效期</th></tr></thead>
            <tbody>
              <tr>
                <td>CN-1001</td><td>
                  <MoneyText
                    :amount="11500"
                    currency="CNY"
                    minor
                  />
                </td><td>2026-01-01 起</td>
              </tr>
            </tbody>
          </VTable>
          <VCardText>
            <VFileInput
              label="追加合同附件（可选）"
              accept=".pdf,.doc,.docx,.xlsx"
              prepend-icon="tabler-paperclip"
              multiple
              data-test="contract-attachment"
              @update:model-value="saveAttachment"
            />
          </VCardText>
        </VCard>
        <VCard
          v-if="props.pageKey === 'I15'"
          title="实盘录入"
          class="mb-6"
        >
          <VCardText>
            <AppTextField
              v-model="actualQty"
              label="实盘数量"
              :disabled="data.detail.status !== 'pending'"
            />
          </VCardText>
        </VCard>
        <VCard :title="props.pageKey === 'S10' ? '供应商报价' : '流程节点'">
          <VCardText>
            <VStepper
              v-if="props.pageKey !== 'S10'"
              :model-value="data.detail.steps.findIndex(step => step.status === 'open') + 1"
              alt-labels
            >
              <VStepperItem
                v-for="(step, index) in data.detail.steps"
                :key="step.id"
                :value="index + 1"
                :title="step.title"
                :complete="step.status === 'done'"
              >
                {{ step.detail }}
              </VStepperItem>
            </VStepper>
            <VRow v-else>
              <VCol
                v-for="row in data.rows"
                :key="row.id"
                cols="12"
                md="4"
              >
                <VCard
                  variant="tonal"
                  :color="row.status === 'recommended' ? 'primary' : undefined"
                >
                  <VCardItem><VCardTitle>{{ stringValue(row, 'supplier') }}</VCardTitle><VCardSubtitle>{{ stringValue(row, 'leadTime') }}</VCardSubtitle></VCardItem>
                  <VCardText>
                    <div class="text-h6 mb-3">
                      <MoneyText
                        :amount="Number(row.total)"
                        currency="CNY"
                        minor
                      />
                    </div>
                    <div class="text-body-2">
                      含税单价：<MoneyText
                        :amount="Number(row.unitPrice)"
                        currency="CNY"
                        minor
                      />
                    </div>
                  </VCardText>
                  <VCardActions>
                    <VBtn
                      data-test="award-rfq"
                      :disabled="row.status === 'recommended'"
                      @click="act('award-rfq', { id: row.id })"
                    >
                      {{ row.status === 'recommended' ? '已选定' : '选择供应商并转采购单' }}
                    </VBtn>
                  </VCardActions>
                </VCard>
              </VCol>
            </VRow>
          </VCardText>
        </VCard>
      </DetailPage>
    </template>

    <template v-else-if="data && isForm">
      <FormPage
        :title="data.title"
        :subtitle="data.subtitle"
        :saving="saving"
        @save="saveForm"
        @cancel="router.back()"
      >
        <template v-if="props.pageKey === 'INT01'">
          <VStepper
            v-model="wizardStep"
            class="mb-6"
          >
            <VStepperItem
              :value="1"
              title="上传文件"
            /><VStepperItem
              :value="2"
              title="确认列映射"
            /><VStepperItem
              :value="3"
              title="预览"
            /><VStepperItem
              :value="4"
              title="导入完成"
            />
          </VStepper>
          <template v-if="wizardStep === 1">
            <AppSelect
              v-model="form.source"
              label="数据来源"
              :items="['领星', '赛狐']"
              class="mb-4"
            />
            <VFileInput
              v-model="uploadFile"
              label="上传 CSV/XLSX"
              accept=".csv,.xlsx,.xls"
              data-test="import-file"
            />
          </template>
          <template v-else-if="wizardStep === 2">
            <VAlert
              type="info"
              variant="tonal"
              class="mb-4"
            >
              AI 已建议 12 个列映射，请逐项确认后导入。AI 只提供建议，不直接导入。
            </VAlert>
            <VTable density="compact">
              <tbody>
                <tr
                  v-for="item in [['订单号', 'order_no'], ['SKU', 'internal_sku'], ['数量', 'qty'], ['金额', 'amount']]"
                  :key="item[0]"
                >
                  <td>{{ item[0] }}</td><td>
                    <AppSelect
                      v-model="mapping[item[1]]"
                      :items="[item[1], '忽略']"
                    />
                  </td><td>
                    <StatusChip
                      domain="mapping"
                      value="suggested"
                    />
                  </td>
                </tr>
              </tbody>
            </VTable>
          </template>
          <template v-else-if="wizardStep === 3">
            <VAlert
              type="info"
              variant="tonal"
              class="mb-4"
            >
              预览显示 248 行，金额和 SKU 字段将按已确认映射写入；确认后才会导入。
            </VAlert>
            <VTable density="compact">
              <thead><tr><th>订单号</th><th>SKU</th><th>数量</th><th>金额</th></tr></thead>
              <tbody><tr><td>SO-2026-001</td><td>CN-1001</td><td>20</td><td>¥ 2,400.00</td></tr></tbody>
            </VTable>
          </template>
          <VAlert
            v-else
            type="success"
            variant="tonal"
          >
            导入完成。原始文件、映射版本和行数已写入集成日志。
          </VAlert>
        </template>
        <template v-else-if="props.pageKey === 'INT03'">
          <AppTextField
            v-model="form.ledgerAccount"
            label="金蝶账套"
            class="mb-4"
          />
          <AppTextField
            v-model="form.voucherType"
            label="凭证字"
            class="mb-4"
          />
          <AppSelect
            v-model="form.exportFormat"
            :items="['xlsx', 'csv']"
            label="导出格式"
            class="mb-4"
          />
          <AppTextField
            v-model="form.endpoint"
            label="科目对照版本"
          />
        </template>
        <template v-else-if="props.pageKey === 'INT04'">
          <AppTextField
            v-model="form.erpnextSite"
            label="ERPNext 站点"
            class="mb-4"
          />
          <AppTextField
            v-model="form.endpoint"
            label="服务地址"
            class="mb-4"
          />
          <AppSelect
            v-model="form.pushMode"
            :items="['审批后可选推送', '仅导出不推送']"
            label="推送策略"
          />
        </template>
        <template v-else-if="props.pageKey === 'SYS20'">
          <VAlert
            type="info"
            variant="tonal"
            class="mb-4"
          >
            签名密钥仅保存服务端引用，页面只显示配置状态。
          </VAlert>
          <VCheckbox
            v-for="channel in ['飞书', '企业微信']"
            :key="channel"
            v-model="imChannelEnabled[channel]"
            :label="`启用 ${channel} 通道`"
          />
          <AppSelect
            v-model="form.channel"
            :items="['报销', '采购', '付款', '盘点差异']"
            label="可在 IM 审批的类型"
            class="mb-4"
          />
          <AppTextField
            v-model="form.threshold"
            label="超过金额必须回网页确认（元）"
            class="mb-4"
          />
          <AppTextField
            v-model="form.endpoint"
            label="回调地址"
            class="mb-4"
          />
          <VChip
            color="success"
            size="small"
          >
            签名密钥：已配置
          </VChip>
        </template>
        <template v-else-if="props.pageKey === 'SYS26'">
          <AppSelect
            v-model="form.channel"
            label="渠道插件"
            :items="['飞书', '企业微信', '钉钉', '邮件', 'Webhook']"
            class="mb-4"
          />
          <AppTextField
            v-model="form.endpoint"
            label="回调地址"
            class="mb-4"
          />
          <AppTextField
            v-model="form.account"
            label="配置密钥"
            type="password"
            hint="密钥只保存服务端引用，页面不会回显"
            persistent-hint
          />
          <VSwitch
            v-model="form.pushMode"
            true-value="启用"
            false-value="停用"
            label="创建后启用渠道"
            class="mt-4"
          />
          <VBtn
            variant="tonal"
            class="mt-4"
            data-test="test-new-channel"
            @click="testChannel"
          >
            测试发送
          </VBtn>
        </template>
        <template v-else>
          <AppTextField
            v-model="form.endpoint"
            label="账套 / 服务地址"
            class="mb-4"
          />
          <AppTextField
            v-model="form.threshold"
            label="IM 审批金额门槛（元）"
            class="mb-4"
          />
          <VSwitch
            label="启用审批卡片"
            model-value
          />
        </template>
        <template #aside>
          <ListPage
            v-if="props.pageKey === 'SYS20'"
            storage-key="gap-b-sys20-channels"
            title="已配置通道"
            :items="data.rows"
            :columns="data.columns"
            embedded
            class="mb-6"
          >
            <template #item.status="{ item }">
              <StatusChip
                domain="generic"
                :value="rowStatus(item)"
              />
            </template>
          </ListPage>
          <VCard
            title="人工确认"
            variant="tonal"
          >
            <VCardText>所有写操作都需要人工确认并记录审计。AI 建议不能替代审批。</VCardText>
          </VCard>
        </template>
      </FormPage>
    </template>

    <template v-else-if="data && props.pageKey === 'D05'">
      <DetailPage
        :title="data.title"
        :subtitle="data.subtitle"
        domain="generic"
        :timeline="(data.chain ?? chainItems.map((item, index) => ({ id: String(index), ...item, status: 'connected' as const }))).map(item => ({ id: item.id, at: item.status === 'connected' ? '已接通' : '待处理', title: item.title, detail: item.detail }))"
      >
        <VCard>
          <VCardText>
            <div class="d-flex gap-3 mb-6">
              <AppTextField
                v-model="search"
                label="订单号 / 单据号"
                placeholder="例如 SO-2026-001"
                data-test="chain-search"
              /><VBtn
                color="primary"
                class="mt-1"
                data-test="chain-search-submit"
                @click="act('search-chain', { query: search })"
              >
                追溯
              </VBtn>
            </div>
            <VRow class="mb-2">
              <VCol
                v-for="item in data.chain ?? []"
                :key="item.id"
                cols="12"
                sm="6"
                md="4"
              >
                <VCard
                  variant="tonal"
                  :color="item.status === 'connected' ? 'success' : 'warning'"
                >
                  <VCardText>
                    <div class="font-weight-medium">{{ item.title }}</div>
                    <div class="text-body-2 mb-2">{{ item.detail }}</div>
                    <VBtn
                      v-if="item.to"
                      :to="item.to"
                      size="small"
                      variant="text"
                      data-test="chain-link"
                    >
                      打开关联单据
                    </VBtn>
                  </VCardText>
                </VCard>
              </VCol>
            </VRow>
            <VBtn
              color="primary"
              variant="tonal"
              data-test="opportunity-win"
              @click="act('win-opportunity')"
            >
              模拟商机赢单并生成订单草稿
            </VBtn>
          </VCardText>
        </VCard>
      </DetailPage>
    </template>

    <template v-else-if="data">
      <div class="d-flex justify-end gap-3 mb-4">
        <PermissionGate
          v-if="props.pageKey === 'S09'"
          action="create"
        >
          <VBtn
            color="primary"
            data-test="create-rfq"
            @click="createRfqOpen = true"
          >
            新建询价单
          </VBtn>
        </PermissionGate>
        <PermissionGate
          v-if="props.pageKey === 'I13'"
          action="create"
        >
          <VBtn
            color="primary"
            data-test="manual-replenishment"
            @click="act('draft-replenishment', { mode: 'manual' })"
          >
            手动新建采购单
          </VBtn>
        </PermissionGate>
        <PermissionGate
          v-if="props.pageKey === 'INT02'"
          action="update"
        >
          <VBtn
            color="primary"
            @click="act('start-sync', { platform: 'Amazon US' })"
          >
            立即同步
          </VBtn>
        </PermissionGate>
        <VBtn
          v-if="props.pageKey === 'SYS25'"
          to="/admin/channels/new"
          color="primary"
        >
          新增渠道
        </VBtn>
      </div>
      <DetailPage
        v-if="props.pageKey === 'SYS19'"
        :title="data.title"
        :subtitle="data.subtitle"
        domain="generic"
      >
        <ListPage
          :storage-key="`gap-b-${props.pageKey}`"
          :title="data.title"
          :subtitle="data.subtitle"
          :items="data.rows"
          :columns="displayColumns"
          :loading="loading"
          embedded
          @open="openRow"
        >
          <template #item.status="{ item }">
            <StatusChip
              domain="generic"
              :value="rowStatus(item)"
            />
          </template>
          <template #item.actions="{ item }">
            <PermissionGate action="update">
              <VBtn
                v-if="rowStatus(item) === 'unbound'"
                size="small"
                variant="text"
                @click="act('bind-channel', { id: item.id, account: 'demo@example.com' })"
              >
                绑定
              </VBtn>
              <VBtn
                v-else
                size="small"
                variant="text"
                @click="act('unbind-channel', { id: item.id })"
              >
                解绑
              </VBtn>
            </PermissionGate>
          </template>
        </ListPage>
      </DetailPage>
      <ListPage
        v-else
        :storage-key="`gap-b-${props.pageKey}`"
        :title="data.title"
        :subtitle="data.subtitle"
        :items="data.rows"
        :columns="displayColumns"
        :loading="loading"
        @open="openRow"
      >
        <template #widgets>
          <VRow v-if="props.pageKey === 'S13'">
            <VCol
              cols="12"
              sm="6"
              md="4"
            >
              <KpiCard
                title="平均评分"
                :value="scoreAverage"
                icon="tabler-chart-arcs"
                hint="评分由确定性代码计算"
              />
            </VCol>
          </VRow>
        </template>
        <template #item.status="{ item }">
          <StatusChip
            :domain="props.pageKey === 'W08' ? 'approval' : props.pageKey === 'SYS25' ? 'generic' : 'generic'"
            :value="rowStatus(item)"
          />
        </template>
        <template #item.amount="{ item }">
          <MoneyText
            v-if="moneyValue(item, 'amount') !== null"
            :amount="moneyValue(item, 'amount') || 0"
            currency="CNY"
            minor
          /><span v-else>{{ stringValue(item, 'amount') }}</span>
        </template>
        <template #item.enabled="{ item }">
          <VSwitch
            :model-value="Boolean(item.enabled)"
            hide-details
            density="compact"
            @update:model-value="toggleChannel(item)"
          />
        </template>
        <template #item.configured="{ item }">
          <VChip
            size="small"
            :color="item.configured ? 'success' : 'secondary'"
          >
            {{ item.configured ? '已配置' : '未配置' }}
          </VChip>
        </template>
        <template #item.actions="{ item }">
          <VBtn
            v-if="props.pageKey === 'I13' && Number(item.suggestedQty) > 0 && showAi"
            size="small"
            variant="text"
            data-test="ai-draft-replenishment"
            @click="act('draft-replenishment', { id: item.id })"
          >
            AI 起草
          </VBtn>
          <VBtn
            v-if="props.pageKey === 'I14'"
            size="small"
            variant="text"
            :disabled="rowStatus(item) === 'posted'"
            @click="act('confirm-transfer', { id: item.id })"
          >
            确认调拨
          </VBtn>
          <VBtn
            v-if="props.pageKey === 'I15'"
            size="small"
            variant="text"
            :disabled="rowStatus(item) !== 'pending'"
            @click="act('submit-count', { id: item.id })"
          >
            提交差异审批
          </VBtn>
          <VBtn
            v-if="props.pageKey === 'I15' && rowStatus(item) === 'submitted'"
            size="small"
            variant="text"
            color="success"
            data-test="approve-count-list"
            @click="act('approve-count', { id: item.id })"
          >
            审批通过并过账
          </VBtn>
          <VBtn
            v-if="props.pageKey === 'W08' && Number(item.amount) <= 5000000"
            size="small"
            variant="text"
            :disabled="rowStatus(item) !== 'pending'"
            data-test="im-approve"
            @click="act('approve-im', { id: item.id })"
          >
            批准
          </VBtn>
          <VBtn
            v-if="props.pageKey === 'W08' && Number(item.amount) <= 5000000"
            size="small"
            variant="text"
            :disabled="rowStatus(item) !== 'pending'"
            @click="act('reject-im', { id: item.id })"
          >
            驳回
          </VBtn>
          <VBtn
            v-if="props.pageKey === 'W08' && Number(item.amount) > 5000000"
            size="small"
            variant="text"
            to="/approvals"
          >
            去网页确认
          </VBtn>
          <VBtn
            v-if="props.pageKey === 'W08'"
            size="small"
            variant="text"
            @click="act('tamper-im', { id: item.id })"
          >
            模拟内容变化
          </VBtn>
          <VBtn
            v-if="props.pageKey === 'W08'"
            size="small"
            variant="text"
            @click="openIm(item)"
          >
            查看卡片
          </VBtn>
          <VBtn
            v-if="props.pageKey === 'SYS25'"
            size="small"
            variant="text"
            @click="act('test-channel', { id: item.id })"
          >
            测试发送
          </VBtn>
          <VBtn
            v-if="props.pageKey === 'SYS25'"
            size="small"
            variant="text"
            @click="toggleChannel(item)"
          >
            {{ item.enabled ? '停用' : '启用' }}
          </VBtn>
        </template>
      </ListPage>
      <FormDrawer
        v-if="props.pageKey === 'S09'"
        v-model="createRfqOpen"
        title="新建询价单"
        :saving="saving"
        @save="saveRfq"
      >
        <AppTextField
          v-model="form.subject"
          label="询价主题"
          class="mb-4"
        />
        <AppTextField
          v-model="form.supplierCount"
          label="供应商数量"
          class="mb-4"
        />
        <AppTextField
          v-model="form.amount"
          label="预计金额（分）"
        />
      </FormDrawer>
      <RecordDrawer
        v-if="props.pageKey === 'W08'"
        v-model="imDrawerOpen"
        :title="selectedImRow?.title ? String(selectedImRow.title) : '审批卡片'"
      >
        <template v-if="selectedImRow">
          <VChip
            :color="rowStatus(selectedImRow) === 'tampered' ? 'error' : 'success'"
            size="small"
            class="mb-4"
          >
            {{ rowStatus(selectedImRow) === 'tampered' ? '内容已变化' : '内容哈希已校验' }}
          </VChip>
          <MoneyText
            :amount="Number(selectedImRow.amount)"
            currency="CNY"
            minor
            class="d-block text-h5 mb-4"
          />
          <div class="text-body-2 mb-4">
            {{ selectedImRow.contentHash }}
          </div>
          <PermissionGate action="approve">
            <VBtn
              v-if="Number(selectedImRow.amount) <= 5000000 && rowStatus(selectedImRow) === 'pending'"
              class="me-2"
              @click="act('approve-im', { id: selectedImRow.id })"
            >
              批准
            </VBtn>
            <VBtn
              v-if="Number(selectedImRow.amount) <= 5000000 && rowStatus(selectedImRow) === 'pending'"
              variant="tonal"
              @click="act('reject-im', { id: selectedImRow.id })"
            >
              驳回
            </VBtn>
          </PermissionGate>
        </template>
      </RecordDrawer>
    </template>
  </div>
</template>
