/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { draftVoucherFromIssue, fetchIssueDetail, resolveIssue } from '@/api/finance'
import FinanceDetail from '@/pages/finance/_components/FinanceDetail.vue'

const route = useRoute(); const router = useRouter(); const row = ref<NonNullable<Awaited<ReturnType<typeof fetchIssueDetail>>> | null>(null); const note = ref(''); const saving = ref(false)

onMounted(async () => { row.value = await fetchIssueDetail(String((route.params as Record<string, string>).id)) })
async function handle(action: 'explained' | 'ignored') { saving.value = true; row.value = await resolveIssue(String((route.params as Record<string, string>).id), action, note.value); saving.value = false }
async function createVoucher() {
  const voucher = await draftVoucherFromIssue(String((route.params as Record<string, string>).id)); if (voucher)
    router.push(`/finance/vouchers/${voucher.id}`)
}
</script>

<template>
  <FinanceDetail
    v-if="row"
    :title="row.code"
    :subtitle="`${row.storeName} · ${row.refNo}`"
    domain="issue"
    :status="row.status"
    :timeline="row.timeline"
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
        </VAlert><VRow>
          <VCol cols="4">
            <div class="text-caption">
              严重级别
            </div><div>{{ row.severity }}</div>
          </VCol><VCol cols="4">
            <div class="text-caption">
              金额
            </div><div>{{ row.amount }} {{ row.currency }}</div>
          </VCol><VCol cols="4">
            <div class="text-caption">
              关联单据
            </div><div>{{ row.refNo }}</div>
          </VCol>
        </VRow>
      </VCardText>
    </VCard><VCard
      title="处理意见"
      class="mb-6"
    >
      <VCardText>
        <AppTextarea
          v-model="note"
          label="说明"
          rows="3"
        /><div class="d-flex gap-3 mt-4">
          <VBtn
            color="success"
            :loading="saving"
            @click="handle('explained')"
          >
            标记已处理
          </VBtn><VBtn
            color="secondary"
            variant="tonal"
            :loading="saving"
            @click="handle('ignored')"
          >
            忽略
          </VBtn><VBtn
            variant="outlined"
            @click="createVoucher"
          >
            生成凭证草稿
          </VBtn>
        </div>
      </VCardText>
    </VCard><VCard title="智能建议">
      <VCardText>AI 仅提供费用分类建议，不计算金额。凭证提交后仍需审批。</VCardText>
    </VCard>
  </FinanceDetail><EmptyState v-else />
</template>

