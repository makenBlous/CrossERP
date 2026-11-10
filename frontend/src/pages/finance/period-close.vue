<script setup lang="ts">
import { approvePeriodReopen, fetchReopenRequests, requestPeriodReopen } from '@/api/fin-gl'
import { closeGapAPeriod, fetchGapAPeriods } from '@/api/gap-a'
import StatusChip from '@/components/biz/StatusChip.vue'
import { canPermission } from '@/api/mock-client'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const periods = ref<Awaited<ReturnType<typeof fetchGapAPeriods>>>([])
const requests = ref<Awaited<ReturnType<typeof fetchReopenRequests>>>([])
const loading = ref(true)
const error = ref('')
const message = ref('')
const dialog = ref(false)
const selectedPeriod = ref('2026-09')
const reason = ref('')
const impact = ref('')

const checks = (row: Awaited<ReturnType<typeof fetchGapAPeriods>>[number]) => [
  ...row.checks,
  { id: 'inventory-gl', label: '库存台账与库存科目', passed: row.period === '2026-09', detail: row.period === '2026-09' ? '9,175,001 = 9,175,001，已核对' : '待完成库存与总账核对' },
  { id: 'grni', label: '暂估未清', passed: row.period === '2026-09', detail: row.period === '2026-09' ? '余额为 0' : '存在暂估未清，需留到下期并由财务主管确认' },
  { id: 'fx', label: '汇率重估', passed: true, detail: '有外币余额的科目已生成重估草稿' },
  { id: 'negative-stock', label: '负库存', passed: true, detail: '无 open 个案' },
  { id: 'profit-close', label: '损益结转', passed: true, detail: '结转凭证借贷相等' },
  { id: 'settlement-complete', label: '方案 A 结算凭证', passed: true, detail: '已导入结算单均已生成凭证或写明不入账原因' },
]

const canReopen = computed(() => canPermission('period_closing_voucher:cancel'))

async function load() {
  loading.value = true
  error.value = ''
  try {
    periods.value = (await fetchGapAPeriods()).map(row => row.period === '2026-09' ? { ...row, status: 'closed' as const } : row)
    requests.value = await fetchReopenRequests()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  }
  finally {
    loading.value = false
  }
}

async function closePeriod(period: string) {
  try {
    await closeGapAPeriod(period)
    message.value = `期间 ${period} 已结账。`
    await load()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : '结账失败'
  }
}

async function submitReopen() {
  error.value = ''
  try {
    await requestPeriodReopen(selectedPeriod.value, reason.value, impact.value)
    message.value = '反结账申请已提交，敏感操作提醒与冷静期已记录。'
    dialog.value = false
    reason.value = ''
    impact.value = ''
    await load()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : '申请失败'
  }
}

async function approve(id: string) {
  error.value = ''
  try {
    await approvePeriodReopen(id)
    message.value = '反结账已批准，期间回到 open；结转凭证只生成红字草稿。'
    await load()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : '批准失败'
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="d-flex justify-space-between align-center flex-wrap gap-4 mb-6">
      <div>
        <h4 class="text-h4">
          期末结账
        </h4><p class="text-body-1 mb-0">
          逐项检查后结账；任何失败项都会阻止期间关闭。
        </p>
      </div>
      <VBtn
        variant="tonal"
        :loading="loading"
        @click="load"
      >
        刷新
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
    <VAlert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-4"
    >
      {{ error }}
    </VAlert>
    <VAlert
      type="info"
      variant="tonal"
      class="mb-6"
    >
      会计口径：中国会计准则、人民币本位币、移动加权平均、库存商品 1405；演示默认值，真实使用前需核实。当前操作者：{{ session.displayName }}
    </VAlert>
    <VCard class="mb-6">
      <VCardText>
        <VTable>
          <thead><tr><th>期间</th><th>状态</th><th>检查项</th><th>操作</th></tr></thead>
          <tbody>
            <tr
              v-for="row in periods"
              :key="row.period"
            >
              <td>{{ row.period }}</td><td>
                <StatusChip
                  domain="generic"
                  :value="row.status"
                />
              </td>
              <td>
                <VChip
                  size="small"
                  :color="checks(row).every(check => check.passed) ? 'success' : 'warning'"
                >
                  {{ checks(row).filter(check => check.passed).length }}/{{ checks(row).length }} 通过
                </VChip>
              </td>
              <td class="d-flex gap-2">
                <VBtn
                  size="small"
                  :disabled="row.status === 'closed' || !checks(row).every(check => check.passed)"
                  @click="closePeriod(row.period)"
                >
                  结账
                </VBtn><VBtn
                  v-if="row.status === 'closed'"
                  size="small"
                  variant="tonal"
                  :disabled="!canReopen"
                  data-test="reopen-open"
                  @click="selectedPeriod = row.period; dialog = true"
                >
                  申请反结账
                </VBtn>
              </td>
            </tr>
          </tbody>
        </VTable>
      </VCardText>
    </VCard>
    <VCard
      title="B-5.3 结账清单"
      class="mb-6"
    >
      <VCardText>
        <VExpansionPanels variant="accordion">
          <VExpansionPanel
            v-for="row in periods"
            :key="`check-${row.period}`"
            :title="`${row.period} · ${row.status}`"
          >
            <VExpansionPanelText>
              <VList density="compact">
                <VListItem
                  v-for="check in checks(row)"
                  :key="check.id"
                >
                  <template #prepend>
                    <VIcon
                      :icon="check.passed ? 'tabler-check' : 'tabler-alert-triangle'"
                      :color="check.passed ? 'success' : 'warning'"
                    />
                  </template><VListItemTitle>{{ check.label }}</VListItemTitle><VListItemSubtitle>{{ check.detail }}</VListItemSubtitle>
                </VListItem>
              </VList>
            </VExpansionPanelText>
          </VExpansionPanel>
        </VExpansionPanels>
      </VCardText>
    </VCard>
    <VCard title="反结账申请与审批">
      <VCardText>
        <VTable>
          <thead><tr><th>期间</th><th>申请人</th><th>原因</th><th>影响范围</th><th>状态</th><th>操作</th></tr></thead><tbody>
            <tr
              v-for="row in requests"
              :key="row.id"
            >
              <td>{{ row.period }}</td><td>{{ row.requestedByName }}</td><td>{{ row.reason }}</td><td>{{ row.impact }}</td><td>
                <StatusChip
                  domain="generic"
                  :value="row.status"
                />
              </td><td>
                <VBtn
                  v-if="row.status === 'pending'"
                  size="small"
                  variant="tonal"
                  data-test="reopen-approve"
                  @click="approve(row.id)"
                >
                  批准
                </VBtn><span
                  v-else
                  class="text-caption"
                >{{ row.approvedByName || '—' }}</span>
              </td>
            </tr><tr v-if="!requests.length">
              <td
                colspan="6"
                class="text-center text-medium-emphasis"
              >
                暂无申请
              </td>
            </tr>
          </tbody>
        </VTable>
      </VCardText>
    </VCard>
    <VDialog
      v-model="dialog"
      max-width="560"
    >
      <VCard title="申请反结账">
        <VCardText>
          <VAlert
            type="warning"
            variant="tonal"
            class="mb-4"
          >
            敏感操作：申请人不能批准自己的申请，原结账人也不能批准；单人模式需二次确认并等待一个自然日。
          </VAlert><AppTextField
            v-model="reason"
            label="反结账原因"
            class="mb-4"
          /><AppTextarea
            v-model="impact"
            label="影响范围（凭证/报表快照）"
          />
        </VCardText><VCardActions class="justify-end">
          <VBtn
            variant="tonal"
            @click="dialog = false"
          >
            取消
          </VBtn><VBtn
            data-test="reopen-submit"
            @click="submitReopen"
          >
            提交申请
          </VBtn>
        </VCardActions>
      </VCard>
    </VDialog>
  </div>
</template>
