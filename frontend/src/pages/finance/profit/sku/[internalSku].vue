/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchProfit } from '@/api/finance'
import FinanceDetail from '@/pages/finance/_components/FinanceDetail.vue'

const route = useRoute(); const payload = ref<Awaited<ReturnType<typeof fetchProfit>>>(); const row = computed(() => payload.value?.rows.find(item => item.sku === String((route.params as Record<string, string>).internalSku)))

onMounted(async () => { payload.value = await fetchProfit() })
</script>

<template>
  <FinanceDetail
    v-if="row"
    :title="`${row.sku} · SKU 利润`"
    :subtitle="`${row.storeName} · 2026-10`"
  >
    <VAlert
      type="info"
      variant="tonal"
      class="mb-6"
    >
      广告成本来源：广告分摊；未配置分摊的订单沿用演示计提 5%。页面只展示服务层已计算结果。
    </VAlert><VRow>
      <VCol
        v-for="item in [{ label: '收入', value: row.revenue }, { label: '平台费', value: row.platformFee }, { label: '广告', value: row.ads }, { label: '头程', value: row.firstMile }, { label: '成本', value: row.cost }, { label: '利润', value: row.profit }]"
        :key="item.label"
        cols="6"
        md="4"
      >
        <KpiCard
          :title="item.label"
          :value="`${item.value} ${row.currency}`"
          icon="tabler-chart-bar"
          color="primary"
        />
      </VCol>
    </VRow>
  </FinanceDetail><EmptyState v-else />
</template>

