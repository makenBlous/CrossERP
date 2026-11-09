<script setup lang="ts">
import { fetchOrders } from '@/api/orders'
import type { OrderSummary } from '@/types/domain'
import { formatMoney } from '@/utils/format'

const { t } = useI18n({ useScope: 'global' })
const orders = ref<OrderSummary[]>([])
const keyword = ref('')
const storeId = ref('all')

onMounted(async () => {
  orders.value = await fetchOrders()
})

const storeItems = computed(() => {
  const names = [...new Set(orders.value.map(item => item.storeId))]

  return [
    { title: t('common.allStores'), value: 'all' },
    ...names.map(id => ({
      title: orders.value.find(item => item.storeId === id)?.storeName ?? id,
      value: id,
    })),
  ]
})

const filtered = computed(() => orders.value.filter(item => {
  const storeOk = storeId.value === 'all' || item.storeId === storeId.value
  const text = `${item.orderNo} ${item.storeName}`.toLowerCase()

  return storeOk && text.includes(keyword.value.trim().toLowerCase())
}))

const headers = computed(() => [
  { title: t('orders.orderNo'), key: 'orderNo' },
  { title: t('common.store'), key: 'storeName' },
  { title: t('orders.date'), key: 'orderedAt' },
  { title: t('common.status'), key: 'status' },
  { title: t('orders.fulfillment'), key: 'fulfillment' },
  { title: t('orders.itemTotal'), key: 'itemTotal', align: 'end' as const },
  { title: t('orders.net'), key: 'net', align: 'end' as const },
  { title: '', key: 'actions', sortable: false },
])
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        {{ t('orders.title') }}
      </h4>
      <p class="text-body-1 text-medium-emphasis mb-0">
        {{ t('orders.subtitle') }} {{ t('common.fromSystem') }}
      </p>
    </div>
    <VCard>
      <VCardText class="d-flex flex-wrap gap-4">
        <AppTextField
          v-model="keyword"
          :label="t('orders.orderNo')"
          style="max-width: 280px;"
        />
        <AppSelect
          v-model="storeId"
          :items="storeItems"
          :label="t('common.store')"
          style="max-width: 280px;"
        />
      </VCardText>
      <VDataTable
        :headers="headers"
        :items="filtered"
        :items-per-page="10"
      >
        <template #item.itemTotal="{ item }">
          {{ formatMoney(item.itemTotal, item.currency) }}
        </template>
        <template #item.net="{ item }">
          {{ formatMoney(item.net, item.currency) }}
        </template>
        <template #item.actions="{ item }">
          <VBtn
            size="small"
            variant="text"
            :to="`/orders/${item.id}`"
          >
            {{ t('common.view') }}
          </VBtn>
        </template>
        <template #no-data>
          {{ t('common.noData') }}
        </template>
      </VDataTable>
    </VCard>
  </div>
</template>
