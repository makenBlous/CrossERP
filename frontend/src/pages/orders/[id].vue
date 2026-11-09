<script setup lang="ts">
import { fetchOrder } from '@/api/orders'
import type { OrderDetail } from '@/types/domain'
import { formatMoney } from '@/utils/format'

const route = useRoute()
const { t } = useI18n({ useScope: 'global' })
const order = ref<OrderDetail | null>(null)
const loaded = ref(false)

const orderId = computed(() => {
  const params = route.params as Record<string, string | string[] | undefined>
  const value = params.id

  return Array.isArray(value) ? value[0] ?? '' : value ?? ''
})

async function load() {
  loaded.value = false
  order.value = await fetchOrder(orderId.value)
  loaded.value = true
}

onMounted(load)
watch(orderId, load)
</script>

<template>
  <div>
    <VBtn
      variant="text"
      class="mb-4"
      prepend-icon="tabler-arrow-left"
      to="/orders"
    >
      {{ t('orders.title') }}
    </VBtn>

    <VAlert
      v-if="loaded && !order"
      type="warning"
      variant="tonal"
    >
      {{ t('orders.missing') }}
    </VAlert>

    <template v-else-if="order">
      <div class="d-flex flex-wrap justify-space-between gap-4 mb-6">
        <div>
          <h4 class="text-h4">
            {{ order.orderNo }}
          </h4>
          <p class="text-body-1 text-medium-emphasis mb-0">
            {{ order.storeName }} · {{ order.platform }} {{ order.marketplace }} · {{ order.orderedAt }}
          </p>
        </div>
        <VChip color="primary">
          {{ order.status }}
        </VChip>
      </div>

      <VRow class="mb-2">
        <VCol
          cols="12"
          sm="6"
          md="3"
        >
          <KpiCard
            :title="t('orders.itemTotal')"
            :value="formatMoney(order.itemTotal, order.currency)"
            icon="tabler-receipt"
          />
        </VCol>
        <VCol
          cols="12"
          sm="6"
          md="3"
        >
          <KpiCard
            :title="t('orders.fees')"
            :value="formatMoney(order.feeTotal, order.currency)"
            icon="tabler-receipt-tax"
            color="warning"
          />
        </VCol>
        <VCol
          cols="12"
          sm="6"
          md="3"
        >
          <KpiCard
            :title="t('orders.refund')"
            :value="formatMoney(order.refund, order.currency)"
            icon="tabler-arrow-back"
            color="error"
          />
        </VCol>
        <VCol
          cols="12"
          sm="6"
          md="3"
        >
          <KpiCard
            :title="t('orders.net')"
            :value="formatMoney(order.net, order.currency)"
            icon="tabler-cash"
            color="success"
          />
        </VCol>
      </VRow>

      <VRow>
        <VCol
          cols="12"
          lg="7"
        >
          <VCard class="mb-6">
            <VCardItem>
              <VCardTitle>{{ t('orders.lines') }}</VCardTitle>
            </VCardItem>
            <VTable>
              <thead>
                <tr>
                  <th>{{ t('orders.sku') }}</th>
                  <th>{{ t('orders.qty') }}</th>
                  <th class="text-end">
                    {{ t('orders.unitPrice') }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="line in order.lines"
                  :key="line.sku"
                >
                  <td>
                    <div class="font-weight-medium">
                      {{ line.sku }}
                    </div>
                    <div class="text-caption">
                      {{ line.title }}
                    </div>
                  </td>
                  <td>{{ line.qty }}</td>
                  <td class="text-end">
                    {{ formatMoney(line.unitPrice, line.currency) }}
                  </td>
                </tr>
              </tbody>
            </VTable>
          </VCard>

          <VCard>
            <VCardItem>
              <VCardTitle>{{ t('orders.feeSplit') }}</VCardTitle>
              <VCardSubtitle>{{ t('common.fromSystem') }}</VCardSubtitle>
            </VCardItem>
            <VTable>
              <thead>
                <tr>
                  <th>{{ t('orders.feeType') }}</th>
                  <th class="text-end">
                    {{ t('common.amount') }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="fee in order.fees"
                  :key="fee.type"
                >
                  <td>{{ fee.type }}</td>
                  <td class="text-end">
                    {{ formatMoney(fee.amount, fee.currency) }}
                  </td>
                </tr>
              </tbody>
            </VTable>
          </VCard>
        </VCol>
        <VCol
          cols="12"
          lg="5"
        >
          <VCard class="mb-6">
            <VCardItem>
              <VCardTitle>{{ t('orders.logistics') }}</VCardTitle>
            </VCardItem>
            <VCardText>
              <div class="mb-2">
                <span class="text-medium-emphasis">{{ t('orders.warehouse') }}：</span>{{ order.shipment.warehouse }}
              </div>
              <div class="mb-2">
                <span class="text-medium-emphasis">{{ t('orders.carrier') }}：</span>{{ order.shipment.carrier }}
              </div>
              <div class="mb-2">
                <span class="text-medium-emphasis">{{ t('orders.tracking') }}：</span>{{ order.shipment.trackingNo }}
              </div>
              <div><span class="text-medium-emphasis">{{ order.fulfillment }}</span> · {{ order.shipment.shippedAt }}</div>
            </VCardText>
          </VCard>
          <VCard>
            <VCardItem>
              <VCardTitle>{{ t('orders.timeline') }}</VCardTitle>
            </VCardItem>
            <VCardText>
              <VTimeline
                side="end"
                density="compact"
                truncate-line="both"
              >
                <VTimelineItem
                  v-for="event in order.timeline"
                  :key="event.time"
                  dot-color="primary"
                  size="x-small"
                >
                  <div class="text-caption text-medium-emphasis">
                    {{ event.time }}
                  </div>
                  <div class="font-weight-medium">
                    {{ event.title }}
                  </div>
                  <div class="text-body-2">
                    {{ event.detail }}
                  </div>
                </VTimelineItem>
              </VTimeline>
            </VCardText>
          </VCard>
        </VCol>
      </VRow>
    </template>
  </div>
</template>
