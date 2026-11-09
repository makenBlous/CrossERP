<script setup lang="ts">
import { fetchVoucherDetail, submitVoucherApproval } from '@/api/finance'
import DetailPage from '@/components/biz/DetailPage.vue'
import EmptyState from '@/components/biz/EmptyState.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const session = useSessionStore()
const row = ref<NonNullable<Awaited<ReturnType<typeof fetchVoucherDetail>>> | null>(null)
const submitting = ref(false)
const message = ref('')

const canSubmit = computed(() => Boolean(row.value && ['draft', 'rejected'].includes(row.value.status) && ['admin', 'operator'].includes(session.role)))

onMounted(async () => {
  row.value = await fetchVoucherDetail(String((route.params as Record<string, string>).id))
})

async function submit() {
  if (!row.value || !canSubmit.value)
    return
  submitting.value = true

  const approval = await submitVoucherApproval(row.value.id)

  submitting.value = false
  if (approval) {
    row.value = await fetchVoucherDetail(row.value.id)
    message.value = '已提交审批，过账由后端 ledger 服务执行。'
  }
}
</script>

<template>
  <DetailPage
    v-if="row"
    :title="row.no"
    :subtitle="`${row.period} · ${row.submitter}`"
    domain="voucher"
    :status="row.status"
    :timeline="row.timeline"
    :related="row.approvalId ? [{ id: row.approvalId, type: '审批', label: '查看审批记录', to: `/approvals/${row.approvalId}` }] : []"
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
        v-if="row.status === 'approved' && ['finance', 'admin'].includes(session.role)"
        variant="tonal"
        prepend-icon="tabler-download"
        @click="message = '已生成并下载通用 Excel 凭证文件。'"
      >
        下载已批准文件
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
            <th>科目</th>
            <th>摘要</th>
            <th class="text-end">
              借方
            </th>
            <th class="text-end">
              贷方
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="line in row.lines"
            :key="line.seq"
          >
            <td>{{ line.account }}</td>
            <td>{{ line.summary }}</td>
            <td class="text-end">
              <MoneyText
                v-if="line.debit"
                :amount="line.debit"
                minor
                currency="CNY"
              />
              <span v-else>—</span>
            </td>
            <td class="text-end">
              <MoneyText
                v-if="line.credit"
                :amount="line.credit"
                minor
                currency="CNY"
              />
              <span v-else>—</span>
            </td>
          </tr>
        </tbody>
      </VTable>
      <VCardText class="d-flex align-center gap-3 flex-wrap">
        <VChip
          :color="row.balanced ? 'success' : 'error'"
          size="small"
        >
          {{ row.balanced ? '借贷平衡' : `差额 ${row.difference}` }}
        </VChip>
        <span class="text-body-2">借方合计：<MoneyText
          :amount="row.debit"
          minor
          currency="CNY"
        /></span>
        <span class="text-body-2">贷方合计：<MoneyText
          :amount="row.credit"
          minor
          currency="CNY"
        /></span>
      </VCardText>
    </VCard>
    <VAlert
      type="info"
      variant="tonal"
    >
      过账由后端 ledger 服务执行；本页面不会直接写账。
    </VAlert>
  </DetailPage>
  <EmptyState
    v-else
    title="未找到凭证"
    text="该凭证 ID 不存在。"
    back-to="/finance/vouchers"
  />
</template>
