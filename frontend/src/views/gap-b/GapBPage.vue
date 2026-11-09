<script setup lang="ts">
import { fetchGapBPage, submitGapBAction } from '@/api/gap-b'
import DetailPage from '@/components/biz/DetailPage.vue'
import FormPage from '@/components/biz/FormPage.vue'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
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
const form = reactive({ source: '领星', fileName: '', subject: '', supplierCount: '2', amount: '120000', channel: '钉钉', account: '', endpoint: '', threshold: '50000' })
const wizardStep = ref(1)

const id = computed(() => {
  const value = (route.params as Record<string, string | string[] | undefined>).id

  return Array.isArray(value) ? value[0] : value
})

const showAi = computed(() => ai.isEnabled)
const isDegraded = computed(() => ai.isReadOnly)
const isDetail = computed(() => Boolean(data.value?.detail))
const isForm = computed(() => data.value?.kind === 'form')

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

async function saveForm() {
  if (props.pageKey === 'INT01') {
    if (wizardStep.value === 1) {
      await act('upload-import')
      wizardStep.value = 2

      return
    }
    await act('confirm-import')
    wizardStep.value = 3

    return
  }
  if (props.pageKey === 'SYS26') {
    await act('create-channel', { channel: form.channel })

    return
  }
  await act('save-settings')
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

    <template v-if="loading">
      <VCard><VSkeletonLoader type="heading, paragraph, table-row@5" /></VCard>
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
                      :model-value="item[1]"
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
          <VAlert
            v-else
            type="success"
            variant="tonal"
          >
            导入完成。原始文件、映射版本和行数已写入集成日志。
          </VAlert>
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
        </template>
        <template v-else>
          <VAlert
            v-if="props.pageKey === 'SYS20'"
            type="info"
            variant="tonal"
            class="mb-4"
          >
            超过门槛的付款卡片只能去网页确认；签名密钥只显示配置状态。
          </VAlert>
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
      <VCard
        :title="data.title"
        :subtitle="data.subtitle"
      >
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
          <VAlert
            v-if="message"
            type="success"
            variant="tonal"
            class="mb-4"
          >
            {{ message }}
          </VAlert>
          <VTimeline
            side="end"
            align="start"
            line-color="success"
          >
            <VTimelineItem
              v-for="item in [{ title: '客户 / 商机', detail: 'Acme Europe · 赢单', ok: true }, { title: '销售订单', detail: 'SO-2026-001 · 客户和商机已关联', ok: true }, { title: 'SKU → 采购 → 入库', detail: 'CN-1001 · PO-2026-001 · 华东 FBA', ok: true }, { title: '头程 / 出库 / 发货', detail: 'FBA 批次 FM-2026-004 · 运单已关联', ok: true }, { title: '凭证', detail: 'VCH-2026-018 · 可回溯来源单据', ok: true }]"
              :key="item.title"
              dot-color="success"
            >
              <div class="font-weight-medium">
                {{ item.title }}
              </div><div class="text-body-2">
                {{ item.detail }}
              </div><VChip
                color="success"
                size="small"
                class="mt-2"
              >
                已接通
              </VChip>
            </VTimelineItem>
          </VTimeline>
        </VCardText>
      </VCard>
    </template>

    <template v-else-if="data">
      <div class="d-flex justify-end gap-3 mb-4">
        <VBtn
          v-if="props.pageKey === 'S09'"
          color="primary"
          data-test="create-rfq"
          @click="act('create-rfq', { subject: form.subject || '新建补货询价', supplierCount: form.supplierCount, amount: form.amount })"
        >
          新建询价单
        </VBtn>
        <VBtn
          v-if="props.pageKey === 'I13'"
          color="primary"
          data-test="manual-replenishment"
          @click="act('draft-replenishment', { mode: 'manual' })"
        >
          手动新建采购单
        </VBtn>
        <VBtn
          v-if="props.pageKey === 'INT02'"
          color="primary"
          @click="act('start-sync', { platform: 'Amazon US' })"
        >
          立即同步
        </VBtn>
        <VBtn
          v-if="props.pageKey === 'SYS25'"
          to="/admin/channels/new"
          color="primary"
        >
          新增渠道
        </VBtn>
      </div>
      <VCard
        v-if="props.pageKey === 'S09'"
        class="mb-4"
      >
        <VCardText class="d-flex gap-3">
          <AppTextField
            v-model="form.subject"
            label="询价主题"
          /><AppTextField
            v-model="form.amount"
            label="预计金额（分）"
          />
        </VCardText>
      </VCard>
      <ListPage
        :storage-key="`gap-b-${props.pageKey}`"
        :title="data.title"
        :subtitle="data.subtitle"
        :items="data.rows"
        :columns="displayColumns"
        :loading="loading"
        @open="openRow"
      >
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
            v-if="props.pageKey === 'SYS19' && rowStatus(item) === 'unbound'"
            size="small"
            variant="text"
            @click="act('bind-channel', { id: item.id, account: 'demo@example.com' })"
          >
            绑定
          </VBtn>
          <VBtn
            v-if="props.pageKey === 'SYS19' && rowStatus(item) === 'bound'"
            size="small"
            variant="text"
            @click="act('unbind-channel', { id: item.id })"
          >
            解绑
          </VBtn>
          <VBtn
            v-if="props.pageKey === 'SYS25'"
            size="small"
            variant="text"
            @click="act('test-channel', { id: item.id })"
          >
            测试发送
          </VBtn>
        </template>
      </ListPage>
    </template>
  </div>
</template>
