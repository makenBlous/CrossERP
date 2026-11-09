/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchVoucherDetail } from '@/api/finance'
import FinanceDetail from '@/pages/finance/_components/FinanceDetail.vue'

const route = useRoute(); const row = ref<NonNullable<Awaited<ReturnType<typeof fetchVoucherDetail>>> | null>(null)

onMounted(async () => { row.value = await fetchVoucherDetail(String((route.params as Record<string, string>).id)) })
</script>

<template>
  <FinanceDetail
    v-if="row"
    :title="row.no"
    :subtitle="`${row.period} · ${row.submitter}`"
    domain="voucher"
    :status="row.status"
    :timeline="row.timeline"
  >
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
          <tr
            v-for="line in row.lines"
            :key="line.seq"
          >
            <td>{{ line.account }}</td><td>{{ line.summary }}</td><td class="text-end">
              {{ line.debit || '—' }}
            </td><td class="text-end">
              {{ line.credit || '—' }}
            </td>
          </tr>
        </tbody>
      </VTable><VCardText>
        <VChip
          color="success"
          size="small"
        >
          借贷平衡
        </VChip><VAlert
          type="info"
          variant="tonal"
          class="mt-4"
        >
          过账由后端 ledger 服务执行；本页面不会直接写账。
        </VAlert>
      </VCardText>
    </VCard>
  </FinanceDetail><EmptyState v-else />
</template>

