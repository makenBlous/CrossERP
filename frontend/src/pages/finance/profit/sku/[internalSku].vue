<script setup lang="ts">
import { fetchProfitSku } from '@/api/finance'
import FinanceDetail from '@/views/finance/FinanceDetail.vue'

const route = useRoute()
const payload = ref<Awaited<ReturnType<typeof fetchProfitSku>>>()
const row = computed(() => payload.value?.row)

onMounted(async () => {
  payload.value = await fetchProfitSku(String((route.params as Record<string, string>).internalSku))
})
</script>

<template>
  <FinanceDetail
    v-if="row"
    :title="`${row.sku} · SKU 利润`"
    :subtitle="`${row.storeName} · ${payload?.period ?? ''}`"
  >
    <VAlert
      v-if="payload?.exampleData"
      type="warning"
      variant="tonal"
      class="mb-6"
    >
      当前期间没有该 SKU 的利润行，以下展示最近有数据的期间 {{ payload?.period }}（示例数据）。
    </VAlert>
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
    <VAlert type="info" variant="tonal">
      来源：广告分摊（金额由服务层已计算结果提供）。
    </VAlert>
    <VCard class="mt-6">
      <VCardItem>
        <VCardTitle>来源订单</VCardTitle>
        <VCardSubtitle>期间 {{ payload?.period }} · 可追溯到订单明细</VCardSubtitle>
      </VCardItem>
      <VTable v-if="payload?.sourceOrders?.length">
        <thead>
          <tr>
            <th>订单</th>
            <th>日期</th>
            <th>店铺</th>
            <th class="text-end">数量</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in payload?.sourceOrders ?? []" :key="order.id">
            <td><RouterLink :to="`/orders/${order.id}`">{{ order.orderNo }}</RouterLink></td>
            <td>{{ order.orderedAt }}</td>
            <td>{{ order.storeName }}</td>
            <td class="text-end">{{ order.qty }}</td>
            <td>{{ order.status }}</td>
          </tr>
        </tbody>
      </VTable>
      <VCardText v-else>
        <EmptyState title="该期间没有可追溯订单" />
      </VCardText>
    </VCard>
  </FinanceDetail>
  <EmptyState
    v-else
    title="未找到 SKU 利润"
    back-to="/finance/profit"
  />
</template>
