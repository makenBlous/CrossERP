<script setup lang="ts">
import { draftVoucherFromIssue, fetchIssueDetail, resolveIssue } from '@/api/finance'
import DetailPage from '@/components/biz/DetailPage.vue'
import EmptyState from '@/components/biz/EmptyState.vue'
import MoneyText from '@/components/biz/MoneyText.vue'

const route = useRoute()
const router = useRouter()
const row = ref<NonNullable<Awaited<ReturnType<typeof fetchIssueDetail>>> | null>(null)
const note = ref('')
const saving = ref(false)

onMounted(async () => {
  row.value = await fetchIssueDetail(String((route.params as Record<string, string>).id))
  note.value = row.value?.summary ?? ''
})

async function handle(action: 'explained' | 'ignored') {
  saving.value = true
  row.value = await resolveIssue(String((route.params as Record<string, string>).id), action, note.value)
  saving.value = false
}

async function createVoucher() {
  const voucher = await draftVoucherFromIssue(String((route.params as Record<string, string>).id))
  if (voucher)
    router.push(`/finance/vouchers/${voucher.id}`)
}
</script>

<template>
  <DetailPage
    v-if="row"
    :title="row.code"
    :subtitle="`${row.storeName} · ${row.refNo}`"
    domain="issue"
    :status="row.status"
    :related="[{ id: row.refNo, type: '来源行', label: row.refNo, to: `/finance/rows/raw/row-42` }]"
  >
    <VCard
      title="异常详情"
      class="mb-6"
    >
      <VCardText>
        <VAlert
          type="warning"
          variant="tonal"
          class="mb-4"
        >
          {{ row.summary }}
        </VAlert>
        <VRow>
          <VCol cols="4">
            <div class="text-caption">
              严重级别
            </div>
            <div>{{ row.severity }}</div>
          </VCol>
          <VCol cols="4">
            <div class="text-caption">
              金额
            </div>
            <MoneyText
              :amount="row.amount"
              minor
              :currency="row.currency"
            />
          </VCol>
          <VCol cols="4">
            <div class="text-caption">
              关联单据
            </div>
            <div>{{ row.refNo }}</div>
          </VCol>
        </VRow>
      </VCardText>
    </VCard>
    <VCard
      title="处理意见"
      class="mb-6"
    >
      <VCardText>
        <AppTextarea
          v-model="note"
          label="说明"
          rows="3"
        />
        <div class="d-flex gap-3 mt-4 flex-wrap">
          <VBtn
            color="success"
            :loading="saving"
            @click="handle('explained')"
          >
            保存处理意见
          </VBtn>
          <VBtn
            color="secondary"
            variant="tonal"
            :loading="saving"
            @click="handle('ignored')"
          >
            忽略
          </VBtn>
          <VBtn
            variant="outlined"
            @click="createVoucher"
          >
            生成凭证草稿
          </VBtn>
        </div>
      </VCardText>
    </VCard>
    <VCard title="智能建议">
      <VCardText>AI 仅提供费用分类建议，不计算金额。凭证提交后仍需审批。</VCardText>
    </VCard>
  </DetailPage>
  <EmptyState
    v-else
    title="未找到异常"
    text="该异常 ID 不存在。"
    back-to="/finance/issues"
  />
</template>
