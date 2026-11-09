/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchReconDetail } from '@/api/finance'
import FinanceDetail from '@/pages/finance/_components/FinanceDetail.vue'

const route = useRoute(); const row = ref<NonNullable<Awaited<ReturnType<typeof fetchReconDetail>>> | null>(null)

onMounted(async () => { row.value = await fetchReconDetail(String((route.params as Record<string, string>).id)) })
</script>

<template>
  <FinanceDetail
    v-if="row"
    :title="`对账运行 ${row.id}`"
    :subtitle="`${row.storeName} · ${row.period}`"
    :status="row.status"
    domain="issue"
  >
    <VRow class="mb-6">
      <VCol cols="4">
        <KpiCard
          title="已匹配"
          :value="String(row.matched)"
          icon="tabler-check"
          color="success"
        />
      </VCol><VCol cols="4">
        <KpiCard
          title="未匹配"
          :value="String(row.unmatched)"
          icon="tabler-alert-circle"
          color="warning"
        />
      </VCol><VCol cols="4">
        <KpiCard
          title="规则版本"
          value="recon-v1"
          icon="tabler-code"
          color="info"
        />
      </VCol>
    </VRow><VCard title="匹配组">
      <VTable>
        <thead><tr><th>状态</th><th>引用</th><th>金额</th><th>原因</th></tr></thead><tbody>
          <tr
            v-for="group in row.groups"
            :key="group.id"
          >
            <td>
              <VChip
                size="small"
                :color="group.status === 'matched' ? 'success' : 'warning'"
              >
                {{ group.status }}
              </VChip>
            </td><td>{{ group.reference }}</td><td>{{ group.amount }}</td><td>{{ group.reason }}</td>
          </tr>
        </tbody>
      </VTable>
    </VCard>
  </FinanceDetail><EmptyState v-else />
</template>

