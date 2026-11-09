<!-- 页面条件较多，保持批次 A 的单一流程壳；脚本里的短分支不影响业务可读性。 -->
<script setup lang="ts">
/* eslint-disable max-statements-per-line, sonarjs/no-same-line-conditional */
import DetailPage from '@/components/biz/DetailPage.vue'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import FormPage from '@/components/biz/FormPage.vue'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useAiModeStore } from '@/stores/ai-mode'
import { useSessionStore } from '@/stores/session'
import {
  closeGapAPeriod, createGapAClaim, createGapACogsVoucher, createGapAFxVoucher, createGapAPolicy, createGapAProfitVoucher, createGapATrip,
  decideGapAClaim, fetchGapAAudits, fetchGapABudget, fetchGapABudgets, fetchGapAClaim, fetchGapAClaims, fetchGapACogs,
  fetchGapAFx, fetchGapALedger, fetchGapALoan, fetchGapALoans, fetchGapAPeriods,
  fetchGapAPolicies, fetchGapARebates, fetchGapAStatement, fetchGapATrialBalance, fetchGapATrips, fetchGapAVat, generateGapAOrderVoucher,
  offsetGapALoan, repayGapALoan, saveGapABudget, submitGapAClaim,
} from '@/api/gap-a'
import type { BudgetRow, EmployeeLoan, ExpenseClaim, GapAPageKey } from '@/types/gap-a'
import { minorFromDecimal } from '@/utils/money'

const props = defineProps<{ pageKey: GapAPageKey }>()
interface TableRow { id: string; [key: string]: unknown }

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const aiMode = useAiModeStore()
const loading = ref(true)
const errorMessage = ref('')
const rows = ref<TableRow[]>([])
const detail = ref<unknown>(null)
const auditEvents = ref<Array<{ id: string; at: string; actor: string; action: string; detail: string }>>([])
const selectedPeriod = ref('2026-10')
const selectedStore = ref('amz-us')
const selectedGranularity = ref<'per_order' | 'per_settlement' | 'per_period_summary'>('per_settlement')
const budgetInput = ref('10000')
const claimDraft = reactive({ category: '交通', merchant: '', amount: '120', occurredOn: '2026-11-10', note: '', attachmentName: '' })
const aiPrefilled = ref(false)
const loanDrawerOpen = ref(false)
const selectedLoanId = ref('')
const repaymentInput = ref('0')
const policyDrawerOpen = ref(false)
const selectedPolicy = ref<TableRow | null>(null)
const policyInput = ref('0')
const tripCreateMode = ref(false)
const tripDraft = reactive({ destination: '', startOn: '2026-11-18', endOn: '2026-11-20', budget: '2400' })

const titles: Record<GapAPageKey, [string, string]> = {
  EX01: ['报销单列表', '查看自己或下属的报销进度，金额由票面和代码合计。'],
  EX02: ['新建报销', '上传票据后可由智能助手分类并预填，提交前仍由员工确认。'],
  EX03: ['报销详情', '查看明细、票据、审批轨迹与凭证草稿。'],
  EX04: ['借款单', '员工备用金、还款和报销冲抵。'],
  EX05: ['借款详情', '查看借款、还款和冲抵记录。'],
  EX06: ['差旅申请', '出差前申请，出差后可关联报销。'],
  EX07: ['费用标准', '维护住宿、交通、餐补等费用上限。'],
  F23: ['总账 / 明细账', '只展示已存的凭证分录，并提供订单到凭证的确定性生成规则。'],
  F24: ['科目余额表', '期初、本期借贷、期末余额，逐科目校验平衡。'],
  F25: ['利润表', '按期间查看收入、成本和费用，来源可追到总账。'],
  F26: ['资产负债表', '查看资产、负债与权益余额及来源凭证。'],
  F27: ['现金流量表', '查看经营活动现金流及来源凭证。'],
  F28: ['期末结账', '按清单检查后结账；有未审批凭证时系统会拦截。'],
  F29: ['成本结转', '按已确认出库生成借主营业务成本、贷库存商品的凭证草稿。'],
  F30: ['预算', '按部门、科目和月份查看预算执行及预警。'],
  F31: ['预算详情', '查看预算执行明细和调整记录。'],
  F32: ['汇兑损益', '按月末汇率重估外币余额，生成凭证草稿。'],
  F33: ['VAT', '跟踪站点 VAT 销项、进项、申报期与状态。'],
  F34: ['出口退税', '跟踪报关单、进项发票和退税进度。'],
}

const [title, subtitle] = titles[props.pageKey]
const isDetail = computed(() => ['EX03', 'EX05', 'F31'].includes(props.pageKey))
const isForm = computed(() => props.pageKey === 'EX02')
const isTripForm = computed(() => props.pageKey === 'EX06' && tripCreateMode.value)
const canFinance = computed(() => ['admin', 'finance', 'accountant', 'finance_manager'].includes(session.role))
const canManager = computed(() => ['admin', 'operator', 'operations_manager', 'department_manager'].includes(session.role))

const columns = computed(() => {
  const map: Record<string, Array<{ key: string; title: string; align?: 'end' }>> = {
    EX01: [{ key: 'id', title: '编号' }, { key: 'claimant', title: '提交人' }, { key: 'department', title: '部门' }, { key: 'total', title: '金额', align: 'end' }, { key: 'status', title: '状态' }, { key: 'origin', title: '来源' }],
    EX04: [{ key: 'id', title: '借款单' }, { key: 'claimant', title: '员工' }, { key: 'purpose', title: '用途' }, { key: 'amount', title: '借款', align: 'end' }, { key: 'outstanding', title: '未冲余额', align: 'end' }, { key: 'status', title: '状态' }, { key: 'actions', title: '操作' }],
    EX06: [{ key: 'id', title: '申请单' }, { key: 'claimant', title: '申请人' }, { key: 'destination', title: '目的地' }, { key: 'startOn', title: '开始' }, { key: 'endOn', title: '结束' }, { key: 'budget', title: '预算', align: 'end' }, { key: 'status', title: '状态' }],
    EX07: [{ key: 'category', title: '费用类别' }, { key: 'department', title: '部门' }, { key: 'limit', title: '上限', align: 'end' }, { key: 'effectiveFrom', title: '生效日' }, { key: 'active', title: '启用' }, { key: 'actions', title: '操作' }],
    F23: [{ key: 'period', title: '期间' }, { key: 'account', title: '科目' }, { key: 'summary', title: '摘要' }, { key: 'debit', title: '借方', align: 'end' }, { key: 'credit', title: '贷方', align: 'end' }, { key: 'sourceId', title: '来源' }],
    F24: [{ key: 'account', title: '科目' }, { key: 'opening', title: '期初', align: 'end' }, { key: 'debit', title: '借方', align: 'end' }, { key: 'credit', title: '贷方', align: 'end' }, { key: 'closing', title: '期末', align: 'end' }],
    F25: [{ key: 'label', title: '项目' }, { key: 'amount', title: '金额', align: 'end' }, { key: 'sourceIds', title: '来源凭证' }],
    F26: [{ key: 'label', title: '项目' }, { key: 'amount', title: '余额', align: 'end' }, { key: 'sourceIds', title: '来源凭证' }],
    F27: [{ key: 'label', title: '项目' }, { key: 'amount', title: '金额', align: 'end' }, { key: 'sourceIds', title: '来源凭证' }],
    F28: [{ key: 'period', title: '期间' }, { key: 'status', title: '状态' }, { key: 'checks', title: '检查项' }],
    F29: [{ key: 'period', title: '期间' }, { key: 'outboundCount', title: '出库数' }, { key: 'amount', title: '结转金额', align: 'end' }, { key: 'status', title: '状态' }],
    F30: [{ key: 'period', title: '期间' }, { key: 'department', title: '部门' }, { key: 'account', title: '科目' }, { key: 'budget', title: '预算', align: 'end' }, { key: 'actual', title: '实际', align: 'end' }, { key: 'status', title: '状态' }],
    F32: [{ key: 'period', title: '期间' }, { key: 'currency', title: '币种' }, { key: 'closingRate', title: '期末汇率' }, { key: 'balance', title: '余额', align: 'end' }, { key: 'gainLoss', title: '汇兑损益', align: 'end' }, { key: 'status', title: '状态' }],
    F33: [{ key: 'store', title: '站点' }, { key: 'period', title: '申报期' }, { key: 'outputTax', title: '销项税', align: 'end' }, { key: 'inputTax', title: '进项税', align: 'end' }, { key: 'payable', title: '应纳', align: 'end' }, { key: 'dueOn', title: '申报日' }, { key: 'status', title: '状态' }],
    F34: [{ key: 'declarationNo', title: '报关单' }, { key: 'store', title: '店铺' }, { key: 'period', title: '期间' }, { key: 'inputInvoice', title: '进项发票' }, { key: 'amount', title: '金额', align: 'end' }, { key: 'status', title: '状态' }, { key: 'dueOn', title: '预计退税日' }],
  }

  return map[props.pageKey] ?? []
})

function rowAmount(row: TableRow, key: string) { return Number(row[key] ?? 0) }
function currency(row: TableRow) { return (row.currency as 'CNY' | 'USD' | 'EUR' | 'GBP' | 'JPY' | undefined) ?? 'CNY' }
function navigate(id: string) {
  if (props.pageKey === 'EX01')
    router.push(`/expense/claims/${id}`); if (props.pageKey === 'EX04')
    router.push(`/expense/loans/${id}`); if (props.pageKey === 'F30')
    router.push(`/finance/budgets/${id}`)
}
function statusDomain() {
  if (props.pageKey === 'F23')
    return 'voucher' as const
  if (['F25', 'F26', 'F27'].includes(props.pageKey))
    return 'statement' as const
  if (['EX01', 'EX04', 'EX06'].includes(props.pageKey))
    return 'approval' as const

  return 'generic' as const
}
function routeId() {
  const params = route.params as Record<string, string | undefined>

  return params.id ?? route.path.split('/').filter(Boolean).at(-1) ?? ''
}
function setRows(value: unknown[]) {
  rows.value = (value as Array<Record<string, unknown>>).map((item, index) => ({ id: String(item.id ?? `${props.pageKey}-${index + 1}`), ...item }))
}

async function load() {
  loading.value = true; errorMessage.value = ''
  try {
    if (props.pageKey === 'EX01') { setRows(await fetchGapAClaims()) }
    else if (props.pageKey === 'EX04') { setRows(await fetchGapALoans()) }
    else if (props.pageKey === 'EX06') { setRows(await fetchGapATrips()) }
    else if (props.pageKey === 'EX07') { setRows(await fetchGapAPolicies()) }
    else if (props.pageKey === 'F23') { setRows(await fetchGapALedger(selectedPeriod.value)) }
    else if (props.pageKey === 'F24') { setRows(await fetchGapATrialBalance(selectedPeriod.value)) }
    else if (['F25', 'F26', 'F27'].includes(props.pageKey)) { setRows(await fetchGapAStatement(props.pageKey === 'F25' ? 'income' : props.pageKey === 'F26' ? 'balance' : 'cashflow', selectedPeriod.value)) }
    else if (props.pageKey === 'F28') { setRows(await fetchGapAPeriods()) }
    else if (props.pageKey === 'F29') { setRows(await fetchGapACogs()) }
    else if (props.pageKey === 'F30') { setRows(await fetchGapABudgets()) }
    else if (props.pageKey === 'F32') { setRows(await fetchGapAFx()) }
    else if (props.pageKey === 'F33') { setRows(await fetchGapAVat()) }
    else if (props.pageKey === 'F34') { setRows(await fetchGapARebates()) }
    else if (isDetail.value) {
      const id = routeId()

      detail.value = props.pageKey === 'EX03' ? await fetchGapAClaim(id) : props.pageKey === 'EX05' ? await fetchGapALoan(id) : await fetchGapABudget(id)
      auditEvents.value = await fetchGapAAudits(id)
    }
  }
  catch (error) { errorMessage.value = error instanceof Error ? error.message : '加载失败' }
  finally { loading.value = false }
}

onMounted(load)
watch([selectedPeriod, () => props.pageKey], load)

async function run(action: () => Promise<unknown>) {
  errorMessage.value = ''; try { await action(); await load() }
  catch (error) { errorMessage.value = error instanceof Error ? error.message : '操作失败' }
}
async function identifyReceipt() {
  if (!aiMode.isEnabled)
    return; aiPrefilled.value = true; claimDraft.merchant = 'Northwind 户外用品'; claimDraft.amount = '120'; claimDraft.category = '交通'; claimDraft.note = '智能助手按票面字段预填，金额仍由员工确认'; claimDraft.attachmentName = claimDraft.attachmentName || '演示发票-识别.pdf'
}
async function saveClaim() {
  let amount: number; try { amount = minorFromDecimal(claimDraft.amount) }
  catch {
    errorMessage.value = '金额格式不正确'

    return
  } await run(async () => {
    const item = await createGapAClaim({ claimant: session.displayName, department: '运营部', attachmentName: claimDraft.attachmentName || '人工填写', line: { category: claimDraft.category, merchant: claimDraft.merchant || '未填写商户', amount, currency: 'CNY', occurredOn: claimDraft.occurredOn, note: claimDraft.note }, origin: aiPrefilled.value ? 'ai' : 'human', agentSuggestionId: aiPrefilled.value ? `sug-${Date.now()}` : undefined }); if (!item || !('id' in item))
      return; await submitGapAClaim(item.id); router.push(`/expense/claims/${item.id}`)
  })
}
async function saveTrip() {
  let budget: number
  try { budget = minorFromDecimal(tripDraft.budget) }
  catch {
    errorMessage.value = '差旅预算格式不正确'

    return
  }
  await run(async () => {
    await createGapATrip({ claimant: session.displayName, destination: tripDraft.destination || '待填写', startOn: tripDraft.startOn, endOn: tripDraft.endOn, budget, currency: 'CNY' })
    tripCreateMode.value = false
  })
}
async function decideClaim(step: 'manager' | 'finance', status: 'approved' | 'rejected') {
  const id = routeId()

  await run(async () => { await decideGapAClaim(id, step, status) })
}
async function orderVoucher() {
  await run(async () => {
    const item = await generateGapAOrderVoucher(selectedStore.value, selectedGranularity.value); if (item && 'id' in item)
      router.push(`/finance/vouchers/${item.id}`)
  })
}
async function profitVoucher(period: string) {
  await run(async () => {
    const item = await createGapAProfitVoucher(period); if (item && 'id' in item)
      router.push(`/finance/vouchers/${item.id}`)
  })
}
async function closePeriod(period: string) { await run(async () => { await closeGapAPeriod(period) }) }
async function cogsVoucher(period: string) {
  await run(async () => {
    const item = await createGapACogsVoucher(period); if (item && 'id' in item)
      router.push(`/finance/vouchers/${item.id}`)
  })
}
async function fxVoucher(id: string) {
  await run(async () => {
    const item = await createGapAFxVoucher(id); if (item && 'id' in item)
      router.push(`/finance/vouchers/${item.id}`)
  })
}
async function saveBudgetDetail() {
  const id = routeId(); let amount: number; try { amount = minorFromDecimal(budgetInput.value) }
  catch {
    errorMessage.value = '预算金额格式不正确'

    return
  } await run(async () => { await saveGapABudget(id, amount) })
}
async function offsetLoan() {
  const loanId = routeId()

  await run(async () => { await offsetGapALoan(loanId, 'exp-001') })
}
function openRepayment(id: string) {
  selectedLoanId.value = id
  repaymentInput.value = '0'
  loanDrawerOpen.value = true
}
async function repayLoan() {
  let amount: number
  try { amount = minorFromDecimal(repaymentInput.value) }
  catch {
    errorMessage.value = '还款金额格式不正确'

    return
  }
  await run(async () => { await repayGapALoan(selectedLoanId.value, amount); loanDrawerOpen.value = false })
}
function openPolicy(row: TableRow) {
  selectedPolicy.value = row
  policyInput.value = String(Number(row.limit ?? 0) / 10000)
  policyDrawerOpen.value = true
}
async function savePolicy() {
  if (!selectedPolicy.value)
    return
  let amount: number
  try { amount = minorFromDecimal(policyInput.value) }
  catch {
    errorMessage.value = '费用标准格式不正确'

    return
  }
  await run(async () => { await createGapAPolicy(String(selectedPolicy.value?.id), amount); policyDrawerOpen.value = false })
}

const detailClaim = computed(() => detail.value as ExpenseClaim)
const detailLoan = computed(() => detail.value as EmployeeLoan)
const detailBudget = computed(() => detail.value as BudgetRow)
const trialBalanced = computed(() => props.pageKey !== 'F24' || rows.value.reduce((sum, item) => sum + Number(item.debit ?? 0) - Number(item.credit ?? 0), 0) === 0)
const auditTimeline = computed(() => auditEvents.value.map(event => ({ id: event.id, at: event.at, title: event.action, detail: event.detail, actor: event.actor })))
</script>

<template>
  <div>
    <div class="d-flex flex-wrap justify-space-between align-center gap-4 mb-6">
      <div>
        <h4 class="text-h4">
          {{ title }}
        </h4><p class="text-body-1 text-medium-emphasis mb-0">
          {{ subtitle }}
        </p>
      </div>
      <div class="d-flex gap-2">
        <AppSelect
          v-if="['F23', 'F24', 'F25', 'F26', 'F27'].includes(pageKey)"
          v-model="selectedPeriod"
          label="会计期间"
          :items="[{ title: '2026-09', value: '2026-09' }, { title: '2026-10', value: '2026-10' }]"
          style="inline-size: 10rem;"
        />
        <VBtn
          v-if="pageKey === 'EX01'"
          to="/expense/claims/new"
          prepend-icon="tabler-plus"
        >
          新建报销
        </VBtn>
        <VBtn
          v-if="pageKey === 'EX06' && !tripCreateMode"
          prepend-icon="tabler-plus"
          @click="tripCreateMode = true"
        >
          新建差旅申请
        </VBtn>
        <VBtn
          v-if="pageKey === 'F25'"
          color="primary"
          variant="tonal"
          @click="profitVoucher('2026-09')"
        >
          生成 2026-09 利润凭证
        </VBtn>
        <VBtn
          v-if="pageKey === 'F25'"
          color="primary"
          variant="tonal"
          @click="profitVoucher('2026-10')"
        >
          生成 2026-10 利润凭证
        </VBtn>
      </div>
    </div>
    <VAlert
      v-if="errorMessage"
      type="error"
      variant="tonal"
      class="mb-4"
    >
      {{ errorMessage }}
    </VAlert>
    <VAlert
      v-if="aiMode.isEnabled && ['EX01', 'EX02', 'EX03', 'EX04', 'EX06', 'F23', 'F28', 'F29', 'F30', 'F32', 'F33', 'F34'].includes(pageKey)"
      type="info"
      variant="tonal"
      class="mb-6"
    >
      智能助手已启用：只读查询和建议会受当前用户权限约束；涉及金额、凭证和付款的动作最多起草并等待人工审批。
    </VAlert>

    <template v-if="isForm">
      <FormPage
        :title="title"
        :subtitle="subtitle"
        @save="saveClaim"
        @cancel="router.push('/expense/claims')"
      >
        <VRow>
          <VCol
            cols="12"
            md="6"
          >
            <AppTextField
              v-model="claimDraft.attachmentName"
              label="票据附件文件名"
              prepend-inner-icon="tabler-paperclip"
            />
          </VCol>
          <VCol
            cols="12"
            md="6"
            class="d-flex align-end gap-2"
          >
            <VBtn
              v-if="aiMode.isEnabled"
              type="button"
              variant="tonal"
              prepend-icon="tabler-sparkles"
              @click="identifyReceipt"
            >
              AI 识别并预填（L3 分类）
            </VBtn><VChip
              v-if="aiPrefilled"
              color="info"
              size="small"
            >
              AI 预填
            </VChip>
          </VCol>
          <VCol
            cols="12"
            md="4"
          >
            <AppTextField
              v-model="claimDraft.category"
              label="费用类别"
            />
          </VCol>
          <VCol
            cols="12"
            md="4"
          >
            <AppTextField
              v-model="claimDraft.merchant"
              label="商户"
            />
          </VCol>
          <VCol
            cols="12"
            md="4"
          >
            <AppTextField
              v-model="claimDraft.amount"
              label="票面金额（CNY）"
            />
          </VCol>
          <VCol
            cols="12"
            md="4"
          >
            <AppTextField
              v-model="claimDraft.occurredOn"
              label="发生日期"
            />
          </VCol>
          <VCol cols="12">
            <AppTextarea
              v-model="claimDraft.note"
              label="说明"
              rows="3"
            />
          </VCol>
        </VRow>
        <template #aside>
          <VCard title="提交前检查">
            <VCardText>
              <VAlert
                type="info"
                variant="tonal"
              >
                金额以票面为准，合计由代码计算；提交后进入人工审批。
              </VAlert>
              <VChip
                v-if="aiPrefilled"
                color="info"
                size="small"
                class="mt-4"
              >
                AI 预填，已等待员工确认
              </VChip>
            </VCardText>
          </VCard>
        </template>
      </FormPage>
    </template>
    <template v-else-if="isTripForm">
      <FormPage
        :title="title"
        subtitle="出差前提交申请，审批后可关联报销。"
        @save="saveTrip"
        @cancel="tripCreateMode = false"
      >
        <VRow>
          <VCol cols="12">
            <AppTextField
              v-model="tripDraft.destination"
              label="目的地"
            />
          </VCol>
          <VCol
            cols="12"
            md="6"
          >
            <AppDateTimePicker
              v-model="tripDraft.startOn"
              label="开始日期"
              :config="{ dateFormat: 'Y-m-d', allowInput: true }"
            />
          </VCol>
          <VCol
            cols="12"
            md="6"
          >
            <AppDateTimePicker
              v-model="tripDraft.endOn"
              label="结束日期"
              :config="{ dateFormat: 'Y-m-d', allowInput: true }"
            />
          </VCol>
          <VCol cols="12">
            <AppTextField
              v-model="tripDraft.budget"
              label="预算（CNY）"
              type="number"
            />
          </VCol>
        </VRow>
      </FormPage>
    </template>

    <template v-else-if="pageKey === 'EX03' && detail">
      <DetailPage
        :title="detailClaim.id"
        :subtitle="`${detailClaim.claimant} · ${detailClaim.department}`"
        :status="detailClaim.status"
        domain="approval"
        :timeline="auditEvents.length ? auditTimeline : detailClaim.approvalSteps?.map((step: any, index: number) => ({ id: String(index), at: step.actor ? '已处理' : '待处理', title: step.title, detail: step.status, actor: step.actor }))"
        :related="detailClaim.status === 'posted' ? [{ id: 'voucher', type: '凭证草稿', label: '查看报销凭证', to: '/finance/vouchers' }] : []"
      >
        <VCard>
          <VCardText>
            <div class="d-flex justify-space-between align-center mb-4">
              <span class="text-h5">报销合计</span><MoneyText
                :amount="detailClaim.total"
                minor
                currency="CNY"
              />
            </div><VAlert
              v-if="detailClaim.overStandard"
              type="warning"
              variant="tonal"
              class="mb-4"
            >
              超过费用标准 {{ detailClaim.standardLimit / 10000 }} CNY，规则检查会拦截提交。
            </VAlert><VTable density="comfortable">
              <thead>
                <tr>
                  <th>类别</th><th>商户</th><th>日期</th><th class="text-end">
                    金额
                  </th>
                </tr>
              </thead><tbody>
                <tr
                  v-for="line in detailClaim.lines"
                  :key="line.id"
                >
                  <td>{{ line.category }}</td><td>{{ line.merchant }}</td><td>{{ line.occurredOn }}</td><td class="text-end">
                    <MoneyText
                      :amount="line.amount"
                      minor
                      currency="CNY"
                    />
                  </td>
                </tr>
              </tbody>
            </VTable><div class="d-flex gap-3 mt-6">
              <PermissionGate action="create">
                <VBtn
                  v-if="detailClaim.status === 'draft'"
                  @click="run(async () => { await submitGapAClaim(detailClaim.id) })"
                >
                  提交
                </VBtn>
              </PermissionGate><PermissionGate action="approve">
                <VBtn
                  color="success"
                  :disabled="!canManager || detailClaim.status !== 'submitted' || detailClaim.claimant === session.displayName"
                  @click="decideClaim('manager', 'approved')"
                >
                  主管批准
                </VBtn>
              </PermissionGate><PermissionGate action="approve">
                <VBtn
                  color="success"
                  :disabled="!canFinance || detailClaim.status !== 'manager_approved' || detailClaim.claimant === session.displayName"
                  @click="decideClaim('finance', 'approved')"
                >
                  财务批准
                </VBtn>
              </PermissionGate><PermissionGate action="approve">
                <VBtn
                  color="error"
                  variant="tonal"
                  :disabled="detailClaim.status === 'posted' || detailClaim.status === 'rejected'"
                  @click="decideClaim(canFinance ? 'finance' : 'manager', 'rejected')"
                >
                  驳回
                </VBtn>
              </PermissionGate>
            </div>
          </VCardText>
        </VCard>
      </DetailPage>
    </template>
    <template v-else-if="pageKey === 'EX05' && detail">
      <DetailPage
        :title="detailLoan.id"
        :subtitle="`${detailLoan.claimant} · ${detailLoan.purpose}`"
        :status="detailLoan.status"
        domain="approval"
        :timeline="auditEvents.length ? auditTimeline : detailLoan.audit.map(event => ({ id: event.id, at: event.at, title: event.action, detail: event.detail, actor: event.actor }))"
      >
        <VCard>
          <VCardText>
            <VRow>
              <VCol
                cols="12"
                sm="4"
              >
                <KpiCard
                  title="借款"
                  :value="`${detailLoan.amount / 10000} CNY`"
                  icon="tabler-cash"
                />
              </VCol><VCol
                cols="12"
                sm="4"
              >
                <KpiCard
                  title="已结算"
                  :value="`${detailLoan.settled / 10000} CNY`"
                  icon="tabler-check"
                  color="success"
                />
              </VCol><VCol
                cols="12"
                sm="4"
              >
                <KpiCard
                  title="未冲余额"
                  :value="`${detailLoan.outstanding / 10000} CNY`"
                  icon="tabler-clock"
                  color="warning"
                />
              </VCol>
            </VRow><VBtn
              class="mt-4"
              variant="tonal"
              :disabled="detailLoan.outstanding <= 0"
              @click="offsetLoan"
            >
              选择报销单冲抵
            </VBtn>
          </VCardText>
        </VCard>
      </DetailPage>
    </template>
    <template v-else-if="pageKey === 'F31' && detail">
      <DetailPage
        :title="detailBudget.id"
        :subtitle="`${detailBudget.period} · ${detailBudget.department} · ${detailBudget.account}`"
        :status="detailBudget.status"
        domain="generic"
        :timeline="auditTimeline"
      >
        <VCard>
          <VCardText>
            <VRow>
              <VCol
                cols="12"
                sm="4"
              >
                <KpiCard
                  title="预算"
                  :value="`${detailBudget.budget / 10000} CNY`"
                  icon="tabler-calculator"
                />
              </VCol><VCol
                cols="12"
                sm="4"
              >
                <KpiCard
                  title="实际"
                  :value="`${detailBudget.actual / 10000} CNY`"
                  icon="tabler-chart-bar"
                  color="info"
                />
              </VCol><VCol
                cols="12"
                sm="4"
              >
                <KpiCard
                  title="使用率"
                  :value="`${Math.round(detailBudget.actual / detailBudget.budget * 100)}%`"
                  icon="tabler-alert-triangle"
                  color="warning"
                />
              </VCol>
            </VRow><div class="d-flex gap-3 align-end mt-6">
              <AppTextField
                v-model="budgetInput"
                label="调整预算（CNY）"
              /><VBtn @click="saveBudgetDetail">
                保存调整申请（L2）
              </VBtn>
            </div>
          </VCardText>
        </VCard>
      </DetailPage>
    </template>

    <template v-else>
      <VAlert
        v-if="pageKey === 'F24'"
        :type="trialBalanced ? 'success' : 'error'"
        variant="tonal"
        class="mb-6"
      >
        {{ trialBalanced ? '借贷合计平衡，余额可追溯到总账。' : '借贷合计不平衡，请先检查总账明细。' }}
      </VAlert>
      <VCard
        v-if="pageKey === 'F23'"
        class="mb-6"
      >
        <VCardItem title="订单 → 凭证规则">
          <template #append>
            <VChip
              color="warning"
              size="small"
            >
              金额取已存字段
            </VChip>
          </template>
        </VCardItem><VCardText>
          <VRow>
            <VCol
              cols="12"
              md="4"
            >
              <AppSelect
                v-model="selectedStore"
                label="店铺"
                :items="[{ title: 'Northwind Outdoor US', value: 'amz-us' }, { title: 'Northwind Outdoor UK', value: 'amz-uk' }, { title: 'northwind-outdoor.com', value: 'shopify' }]"
              />
            </VCol><VCol
              cols="12"
              md="4"
            >
              <AppSelect
                v-model="selectedGranularity"
                label="生成粒度"
                :items="[{ title: '逐单', value: 'per_order' }, { title: '按结算单', value: 'per_settlement' }, { title: '按期汇总', value: 'per_period_summary' }]"
              />
            </VCol><VCol
              cols="12"
              md="4"
              class="d-flex align-end"
            >
              <VBtn @click="orderVoucher">
                生成收入 / 应收凭证草稿
              </VBtn>
            </VCol>
          </VRow>
        </VCardText>
      </VCard>
      <VCard
        v-if="pageKey === 'F28'"
        class="mb-6"
      >
        <VCardText>
          <VAlert
            type="info"
            variant="tonal"
          >
            结账是人工动作；智能助手只能起草检查清单。
          </VAlert>
        </VCardText>
      </VCard>
      <VCard
        v-if="pageKey === 'F30' && rows.some(item => item.status === 'warning' || item.status === 'exceeded')"
        class="mb-6"
      >
        <VCardText>
          <VAlert
            type="warning"
            variant="tonal"
          >
            预算已达到 80% 以上，消息中心应显示预算预警；实际金额由规则引擎更新。
          </VAlert>
        </VCardText>
      </VCard>
      <ListPage
        :storage-key="`gap-a-${pageKey}`"
        :title="title"
        :subtitle="subtitle"
        :items="rows"
        :columns="columns"
        :filters="pageKey === 'EX01' ? [{ key: 'status', label: '状态', items: [{ title: '已提交', value: 'submitted' }, { title: '已入账', value: 'posted' }, { title: '已驳回', value: 'rejected' }] }] : pageKey === 'EX04' ? [{ key: 'status', label: '状态', items: [{ title: '待审批', value: 'submitted' }, { title: '已批准', value: 'approved' }, { title: '已还清', value: 'repaid' }] }] : []"
        :loading="loading"
        @open="item => navigate(item.id)"
      >
        <template #widgets>
          <VRow class="mb-6">
            <VCol
              cols="12"
              sm="4"
            >
              <KpiCard
                title="记录数"
                :value="String(rows.length)"
                icon="tabler-list-details"
              />
            </VCol><VCol
              cols="12"
              sm="4"
            >
              <KpiCard
                title="待处理"
                :value="String(rows.filter(item => ['pending', 'submitted', 'preview', 'draft'].includes(String(item.status))).length)"
                icon="tabler-clock"
                color="warning"
              />
            </VCol><VCol
              cols="12"
              sm="4"
            >
              <KpiCard
                title="期间"
                :value="selectedPeriod"
                icon="tabler-calendar"
                color="info"
              />
            </VCol>
          </VRow>
        </template>
        <template
          v-for="column in columns"
          :key="column.key"
          #[`item.${column.key}`]="{ item }"
        >
          <RouterLink
            v-if="column.key === 'id' && ['EX01', 'EX04', 'F30'].includes(pageKey)"
            :to="pageKey === 'EX01' ? `/expense/claims/${item.id}` : pageKey === 'EX04' ? `/expense/loans/${item.id}` : `/finance/budgets/${item.id}`"
          >
            {{ item[column.key] }}
          </RouterLink>
          <RouterLink
            v-else-if="column.key === 'sourceId' && pageKey === 'F23'"
            :to="`/finance/vouchers/${item.voucherId}`"
          >
            {{ item[column.key] }}
          </RouterLink>
          <MoneyText
            v-else-if="['total', 'amount', 'outstanding', 'limit', 'budget', 'actual', 'debit', 'credit', 'opening', 'closing', 'outputTax', 'inputTax', 'payable', 'balance', 'gainLoss'].includes(column.key)"
            :amount="rowAmount(item, column.key)"
            minor
            :currency="currency(item)"
          />
          <span v-else-if="column.key === 'status'">
            <StatusChip
              :domain="statusDomain()"
              :value="String(item[column.key])"
            />
            <VBtn
              v-if="pageKey === 'F29'"
              size="x-small"
              variant="text"
              @click.stop="cogsVoucher(String(item.period))"
            >
              生成凭证
            </VBtn>
            <VBtn
              v-if="pageKey === 'F32'"
              size="x-small"
              variant="text"
              @click.stop="fxVoucher(String(item.id))"
            >
              生成凭证
            </VBtn>
          </span>
          <span
            v-else-if="column.key === 'actions'"
            class="d-flex gap-2"
          >
            <VBtn
              v-if="pageKey === 'EX04'"
              size="x-small"
              variant="tonal"
              @click.stop="openRepayment(String(item.id))"
            >
              登记还款
            </VBtn>
            <VBtn
              v-if="pageKey === 'EX07'"
              size="x-small"
              variant="tonal"
              @click.stop="openPolicy(item)"
            >
              编辑标准
            </VBtn>
          </span>
          <span v-else-if="column.key === 'checks'">{{ (item.checks as unknown[]).filter((check: any) => check.passed).length }}/{{ (item.checks as unknown[]).length }} 通过 <VBtn
            size="x-small"
            variant="text"
            :disabled="item.status === 'closed'"
            @click.stop="closePeriod(String(item.period))"
          >结账</VBtn></span>
          <span v-else-if="column.key === 'sourceIds'">{{ (item.sourceIds as string[]).join('、') || '—' }}</span>
          <span v-else-if="column.key === 'active'">{{ item.active ? '启用' : '停用' }}</span>
          <span v-else-if="column.key === 'origin'">{{ item.origin === 'ai' ? '智能体起草' : '人工' }}</span>
          <span v-else>{{ item[column.key] ?? '—' }}</span>
        </template>
      </ListPage>
      <FormDrawer
        v-model="loanDrawerOpen"
        title="登记借款还款"
        @save="repayLoan"
      >
        <AppTextField
          v-model="repaymentInput"
          label="还款金额（CNY）"
          type="number"
        />
        <p class="text-caption text-medium-emphasis mt-2 mb-0">
          还款动作由人工确认，余额由服务层确定性更新。
        </p>
      </FormDrawer>
      <FormDrawer
        v-model="policyDrawerOpen"
        title="编辑费用标准"
        @save="savePolicy"
      >
        <AppTextField
          v-model="policyInput"
          label="费用上限（CNY）"
          type="number"
        />
      </FormDrawer>
    </template>
  </div>
</template>
