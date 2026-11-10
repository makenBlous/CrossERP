<script setup lang="ts">
import { fetchGlReconcile } from '@/api/fin-gl'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import StatusChip from '@/components/biz/StatusChip.vue'

const rows = ref<Awaited<ReturnType<typeof fetchGlReconcile>>>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchGlReconcile()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  }
  finally {
    loading.value = false
  }
}

onMounted(load)

const columns = [
  { key: 'period', title: '期间' },
  { key: 'warehouse', title: '仓库' },
  { key: 'sku', title: 'SKU' },
  { key: 'ledgerBalance', title: '台账余额', align: 'end' as const },
  { key: 'inventoryAccount', title: '库存科目', align: 'end' as const },
  { key: 'inventoryTransit', title: '在途科目', align: 'end' as const },
  { key: 'difference', title: '差异', align: 'end' as const },
  { key: 'status', title: '核对' },
]
</script>

<template>
  <ListPage
    storage-key="inventory-gl-reconcile"
    title="库存与总账核对"
    subtitle="库存台账余额应等于库存商品 + 在途物资科目余额。演示数据来自 D-10。"
    :items="rows"
    :columns="columns"
    :loading="loading"
    :error="error"
    @retry="load"
  >
    <template #widgets>
      <VRow class="mb-6">
        <VCol
          cols="12"
          sm="4"
        >
          <KpiCard
            title="已核对通过"
            :value="String(rows.filter(row => row.status === 'matched').length)"
            icon="tabler-check"
            color="success"
          />
        </VCol>
        <VCol
          cols="12"
          sm="4"
        >
          <KpiCard
            title="有差异"
            :value="String(rows.filter(row => row.status === 'difference').length)"
            icon="tabler-alert-triangle"
            color="warning"
          />
        </VCol>
        <VCol
          cols="12"
          sm="4"
        >
          <KpiCard
            title="演示核对基准"
            value="9,175,001"
            icon="tabler-scale"
            color="info"
            hint="金额以万分位存储"
          />
        </VCol>
      </VRow>
      <VAlert
        type="info"
        variant="tonal"
        class="mb-6"
      >
        演示默认值，真实使用前需核实。库存科目包含 inventory 与 inventory_in_transit；差异行只进入人工处理队列。
      </VAlert>
    </template>
    <template #item.ledgerBalance="{ item }">
      <MoneyText
        :amount="item.ledgerBalance"
        currency="CNY"
        minor
      />
    </template>
    <template #item.inventoryAccount="{ item }">
      <MoneyText
        :amount="item.inventoryAccount"
        currency="CNY"
        minor
      />
    </template>
    <template #item.inventoryTransit="{ item }">
      <MoneyText
        :amount="item.inventoryTransit"
        currency="CNY"
        minor
      />
    </template>
    <template #item.difference="{ item }">
      <MoneyText
        :amount="item.difference"
        currency="CNY"
        minor
      />
    </template>
    <template #item.status="{ item }">
      <StatusChip
        domain="generic"
        :value="item.status === 'matched' ? '通过' : 'difference'"
      />
    </template>
  </ListPage>
</template>
