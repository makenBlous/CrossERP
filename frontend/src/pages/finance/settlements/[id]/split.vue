<script setup lang="ts">
import { fetchSettlementSplit } from '@/api/fin-gl'
import FinanceDetail from '@/views/finance/FinanceDetail.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import StatusChip from '@/components/biz/StatusChip.vue'

const route = useRoute()
const row = ref<Awaited<ReturnType<typeof fetchSettlementSplit>>>(null)
const error = ref('')

onMounted(async () => {
  try {
    const params = route.params as Record<string, string | undefined>

    row.value = await fetchSettlementSplit(String(params.id ?? ''))
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  }
})
</script>

<template>
  <FinanceDetail
    v-if="row"
    :title="`${row.externalId} · 清分`"
    :subtitle="`${row.periodStart} ~ ${row.periodEnd} · 来源 ${row.source === 'sp_api' ? 'API' : row.source === 'plugin' ? '插件' : '文件'}`"
  >
    <VAlert
      type="info"
      variant="tonal"
      class="mb-6"
    >
      一张结算单的清分行统一使用结算结束日汇率 <strong>{{ row.fxRate }}</strong>。映射未确认的行停在 split，不进凭证。
    </VAlert>
    <VRow class="mb-6">
      <VCol
        cols="12"
        md="4"
      >
        <KpiCard
          title="原币打款"
          :value="`${row.payoutAmountFc} USD`"
          icon="tabler-cash"
          color="primary"
        />
      </VCol>
      <VCol
        cols="12"
        md="4"
      >
        <KpiCard
          title="本位币"
          value="¥379.85"
          icon="tabler-currency-yuan"
          color="success"
          hint="53.50 × 7.1000"
        />
      </VCol>
      <VCol
        cols="12"
        md="4"
      >
        <KpiCard
          title="打款汇差"
          value="¥10,700"
          icon="tabler-arrows-exchange"
          color="warning"
          hint="演示金额：1.07 元"
        />
      </VCol>
    </VRow>
    <VCard title="清分明细">
      <VTable>
        <thead>
          <tr>
            <th>桶</th><th>映射科目</th><th>原币</th><th class="text-end">
              本位币
            </th><th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="line in row.splitLines"
            :key="line.id"
          >
            <td>{{ line.bucket }}</td><td>{{ line.mapping }}</td><td>{{ line.amountFc }}</td><td class="text-end">
              <MoneyText
                :amount="line.amountCny"
                currency="CNY"
                minor
              />
            </td><td>
              <StatusChip
                domain="generic"
                :value="line.status === 'confirmed' ? '已确认' : 'suspended'"
              />
            </td>
          </tr>
        </tbody>
      </VTable>
    </VCard>
    <VAlert
      v-if="error"
      type="error"
      variant="tonal"
      class="mt-4"
    >
      {{ error }}
    </VAlert>
  </FinanceDetail>
  <EmptyState
    v-else
    title="未找到结算清分"
    back-to="/finance/settlements"
  />
</template>
