<script setup lang="ts">
import { decideApproval } from '@/api/approvals'
import { fetchPendingVoucherApprovalId, fetchVoucherApprovalIds, fetchVoucherDetail, financeCreatorId, submitBoundGapAVoucher, submitVoucherApproval } from '@/api/finance'
import { draftVoucherReversal } from '@/api/fin-gl'
import { fetchGapAVoucher } from '@/api/gap-a'
import { canPermission } from '@/api/mock-client'
import DetailPage from '@/components/biz/DetailPage.vue'
import EmptyState from '@/components/biz/EmptyState.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import { useSessionStore } from '@/stores/session'
import type { GapAVoucher } from '@/types/gap-a'

const route = useRoute()
const session = useSessionStore()
const row = ref<GapAVoucher | null>(null)
const source = ref<'gap-a' | 'finance'>('gap-a')
const approvalIds = ref<string[]>([])
const pendingApprovalId = ref('')
const message = ref('')
const submitting = ref(false)
const reversalId = ref('')
const reversedById = ref('')

const canSubmitGapA = computed(() => Boolean(row.value && source.value === 'gap-a' && row.value.status === 'draft' && (canPermission('system:create') || canPermission('approval:approve')) && canPermission('agent_suggestion:create')))
const canSubmitFinance = computed(() => Boolean(row.value && source.value === 'finance' && (row.value.status === 'draft' || row.value.status === 'rejected') && canPermission('journal_entry:submit') && canPermission('agent_suggestion:create')))
const canSubmit = computed(() => canSubmitGapA.value || canSubmitFinance.value)
const canApprove = computed(() => Boolean(row.value && source.value === 'gap-a' && row.value.status === 'pending' && pendingApprovalId.value && canPermission('approval:approve') && session.userId !== row.value.createdById))
const canReverse = computed(() => Boolean(row.value && source.value === 'finance' && row.value.status === 'posted' && canPermission('journal_entry:cancel') && !reversedById.value))

function voucherId() {
  return String((route.params as Record<string, string | undefined>).id ?? '')
}

async function load() {
  const id = voucherId()
  const gap = await fetchGapAVoucher(id) as GapAVoucher | null
  if (gap) {
    row.value = gap
    source.value = 'gap-a'
    approvalIds.value = await fetchVoucherApprovalIds(id, 'gap-a').catch(() => [])
    pendingApprovalId.value = await fetchPendingVoucherApprovalId(id, 'gap-a').catch(() => '')

    return
  }

  const finance = await fetchVoucherDetail(id)
  if (!finance) {
    row.value = null
    approvalIds.value = []
    pendingApprovalId.value = ''

    return
  }

  source.value = 'finance'
  approvalIds.value = finance.approvalIds ?? []
  pendingApprovalId.value = ''
  reversalId.value = finance.reversesVoucherId ?? ''
  reversedById.value = finance.reversedByVoucherId ?? ''
  row.value = {
    id: finance.id,
    no: finance.no,
    period: finance.period,
    summary: finance.summary,
    status: finance.status,
    debit: finance.debit,
    credit: finance.credit,
    currency: finance.currency,
    debitAccount: '主营业务成本',
    creditAccount: '平台结算清算',
    sourceLinks: [],
    createdById: financeCreatorId(finance.submitter),
    timeline: (finance.timeline ?? []).map((event, index) => ({ id: `${finance.id}-${index}`, at: event.at, action: event.title, detail: event.detail, actor: event.actor ?? '', origin: 'human' as const })),
  }
}

async function reverse() {
  if (!row.value || !canReverse.value)
    return
  try {
    const draft = await draftVoucherReversal(row.value.id)

    message.value = `已生成红字草稿 ${draft.no}，原凭证保持已过账。`
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '红字冲销失败' }
}

onMounted(load)
async function submit() {
  if (!row.value || !canSubmit.value)
    return
  submitting.value = true
  try {
    if (source.value === 'finance') {
      const approval = await submitVoucherApproval(row.value.id)
      if (!approval)
        throw new Error('凭证未能提交审批')
    }
    else {
      await submitBoundGapAVoucher(row.value.id)
    }
    message.value = '已提交审批，批准前不会写入总账。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '提交失败' }
  finally { submitting.value = false }
}
async function decide(approved: boolean) {
  if (!row.value || !canApprove.value || !pendingApprovalId.value)
    return
  try {
    await decideApproval(pendingApprovalId.value, approved ? 'approved' : 'rejected')
    message.value = approved ? '凭证已批准，可进入总账。' : '凭证已驳回。'
    await load()
  }
  catch (error) { message.value = error instanceof Error ? error.message : '审批失败' }
}
</script>

<template>
  <DetailPage
    v-if="row"
    :title="row.no"
    :subtitle="`${row.period} · ${row.summary}`"
    domain="voucher"
    :status="row.status"
    :timeline="row.timeline.map(event => ({ id: event.id, at: event.at, title: event.action, detail: event.detail, actor: event.actor }))"
    :related="row.sourceLinks.map(link => ({ id: link.sourceId, type: link.sourceType, label: link.label, to: link.to }))"
  >
    <template #actions>
      <VBtn
        v-if="canSubmit"
        prepend-icon="tabler-send"
        :loading="submitting"
        @click="submit"
      >
        提交审批
      </VBtn>
      <VBtn
        v-if="canApprove"
        color="success"
        @click="decide(true)"
      >
        批准
      </VBtn>
      <VBtn
        v-if="canApprove"
        color="error"
        variant="tonal"
        @click="decide(false)"
      >
        驳回
      </VBtn>
      <VBtn
        v-for="approvalId in approvalIds"
        :key="approvalId"
        variant="tonal"
        :to="`/approvals/${approvalId}`"
      >
        查看审批
      </VBtn>
      <VBtn
        v-if="row.status === 'approved'"
        variant="tonal"
        prepend-icon="tabler-download"
        @click="message = '已生成通用 Excel 凭证文件（演示）。'"
      >
        下载已批准文件
      </VBtn>
      <VBtn
        v-if="canReverse"
        variant="tonal"
        color="warning"
        prepend-icon="tabler-arrow-back-up"
        data-test="voucher-reverse"
        @click="reverse"
      >
        红字冲销
      </VBtn>
    </template>
    <VAlert
      v-if="message"
      type="success"
      variant="tonal"
      class="mb-6"
    >
      {{ message }}
    </VAlert>
    <VCard
      title="凭证分录"
      class="mb-6"
    >
      <VTable>
        <thead>
          <tr>
            <th>科目</th><th>摘要</th><th class="text-end">
              借方
            </th><th class="text-end">
              贷方
            </th>
          </tr>
        </thead><tbody>
          <tr>
            <td>{{ row.debitAccount ?? '主营业务成本' }}</td><td>{{ row.summary }}</td><td class="text-end">
              <MoneyText
                :amount="row.debit"
                minor
                currency="CNY"
              />
            </td><td class="text-end">
              —
            </td>
          </tr><tr>
            <td>{{ row.creditAccount ?? '平台结算清算' }}</td><td>{{ row.summary }}</td><td class="text-end">
              —
            </td><td class="text-end">
              <MoneyText
                :amount="row.credit"
                minor
                currency="CNY"
              />
            </td>
          </tr>
        </tbody>
      </VTable><VCardText class="d-flex align-center gap-3 flex-wrap">
        <VChip
          color="success"
          size="small"
        >
          借贷平衡
        </VChip><span>借方合计：<MoneyText
          :amount="row.debit"
          minor
          currency="CNY"
        /></span><span>贷方合计：<MoneyText
          :amount="row.credit"
          minor
          currency="CNY"
        /></span>
      </VCardText>
    </VCard>
    <VCard title="来源追溯">
      <VList>
        <VListItem
          v-for="link in row.sourceLinks"
          :key="link.sourceId"
          :to="link.to"
        >
          <VListItemTitle>{{ link.label }}</VListItemTitle><VListItemSubtitle>
            {{ link.sourceType }} · <MoneyText
              :amount="link.amount"
              minor
              :currency="link.currency"
            />
          </VListItemSubtitle>
        </VListItem>
      </VList>
    </VCard>
    <VCard
      v-if="reversalId || reversedById"
      title="冲销链"
      class="mt-6"
    >
      <VCardText class="d-flex gap-3 flex-wrap">
        <RouterLink
          v-if="reversalId"
          :to="`/finance/vouchers/${reversalId}`"
        >
          红字来源：{{ reversalId }}
        </RouterLink>
        <RouterLink
          v-if="reversedById"
          :to="`/finance/vouchers/${reversedById}`"
        >
          红字凭证：{{ reversedById }}
        </RouterLink>
      </VCardText>
    </VCard>
  </DetailPage>
  <EmptyState
    v-else
    title="未找到凭证"
    text="该凭证 ID 不存在。"
    back-to="/finance/vouchers"
  />
</template>
