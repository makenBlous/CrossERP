<script setup lang="ts">
import { fetchOrder } from '@/api/orders'
import { registerSalesReturn, shipSalesOrder } from '@/api/workflows'
import DetailPage from '@/components/biz/DetailPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import { useConfirm } from '@/composables/useConfirm'
import { usePageContext } from '@/composables/usePageContext'
import type { OrderDetail } from '@/types/domain'
import { formatMoney } from '@/utils/format'
import { readParam } from '@/utils/route-param'

const route = useRoute()
const { t } = useI18n({ useScope: 'global' })
const { confirm } = useConfirm()
const { setSelected } = usePageContext()
const order = ref<OrderDetail | null>(null)
const loaded = ref(false)
const acting = ref(false)
const error = ref('')
const tab = ref('lines')

const orderId = computed(() => readParam(route.params, 'id'))

async function load() {
  loaded.value = false
  error.value = ''
  try {
    order.value = await fetchOrder(orderId.value)
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loaded.value = true
  }
}

onMounted(load)
watch(orderId, load)
watch(order, value => setSelected(value?.id ?? null))
onUnmounted(() => setSelected(null))

const canReturn = computed(() => order.value?.statusCode === 'shipped' || order.value?.statusCode === 'partial_refund')

async function ship() {
  if (!order.value)
    return

  acting.value = true
  error.value = ''
  try {
    await shipSalesOrder(order.value.id)
    await load()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    acting.value = false
  }
}

async function register(disposition: 'restock' | 'scrap') {
  if (!order.value)
    return

  const ok = await confirm({
    title: disposition === 'restock' ? t('orders.restock') : t('orders.scrap'),
    text: order.value.orderNo,
    confirmText: disposition === 'restock' ? t('orders.restock') : t('orders.scrap'),
    cancelText: t('foundation.cancel'),
  })

  if (!ok)
    return

  acting.value = true
  error.value = ''
  try {
    await registerSalesReturn(order.value.id, disposition)
    await load()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    acting.value = false
  }
}
</script>

<template>
  <div>
    <VBtn
      variant="text"
      class="mb-4"
      prepend-icon="tabler-arrow-left"
      :to="{ path: '/orders' }"
    >
      {{ t('orders.title') }}
    </VBtn>
    <VAlert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-4"
    >
      {{ error }}
    </VAlert>
    <LoadingState v-if="!loaded" />
    <VAlert
      v-else-if="!order"
      type="warning"
      variant="tonal"
    >
      {{ t('orders.missing') }}
    </VAlert>
    <DetailPage
      v-else
      :title="order.orderNo"
      :subtitle="`${order.storeName} · ${order.platform} ${order.marketplace} · ${order.orderedAt}`"
      domain="sales_order"
      :status="order.statusCode || ''"
      :timeline="order.timeline.map(item => ({ at: item.time, title: item.title, detail: item.detail }))"
      :related="order.related"
    >
      <template #actions>
        <PermissionGate action="ship">
          <VBtn
            v-if="order.statusCode === 'paid'"
            color="primary"
            data-test="order-ship"
            :loading="acting"
            @click="ship"
          >
            {{ t('orders.ship') }}
          </VBtn>
        </PermissionGate>
        <PermissionGate action="receive">
          <VBtn
            v-if="canReturn"
            variant="tonal"
            :loading="acting"
            @click="register('restock')"
          >
            {{ t('orders.restock') }}
          </VBtn>
        </PermissionGate>
        <PermissionGate action="update">
          <VBtn
            v-if="canReturn"
            variant="tonal"
            color="warning"
            :loading="acting"
            @click="register('scrap')"
          >
            {{ t('orders.scrap') }}
          </VBtn>
        </PermissionGate>
      </template>

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

      <VCard>
        <VTabs
          v-model="tab"
          class="v-tabs-pill"
        >
          <VTab value="lines">
            {{ t('orders.lines') }}
          </VTab>
          <VTab value="fees">
            {{ t('orders.feeSplit') }}
          </VTab>
          <VTab value="ship">
            {{ t('orders.logistics') }}
          </VTab>
        </VTabs>
        <VWindow v-model="tab">
          <VWindowItem value="lines">
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
                    <MoneyText
                      :amount="line.unitPrice"
                      :currency="line.currency"
                    />
                  </td>
                </tr>
              </tbody>
            </VTable>
          </VWindowItem>
          <VWindowItem value="fees">
            <VCardSubtitle class="px-4 pt-4">
              {{ t('common.fromSystem') }}
            </VCardSubtitle>
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
                  v-for="(fee, index) in order.fees"
                  :key="`${fee.type}-${index}`"
                >
                  <td>{{ fee.type }}</td>
                  <td class="text-end">
                    <MoneyText
                      :amount="fee.amount"
                      :currency="fee.currency"
                    />
                  </td>
                </tr>
              </tbody>
            </VTable>
          </VWindowItem>
          <VWindowItem value="ship">
            <VCardText>
              <div class="mb-2">
                {{ t('orders.buyer') }}：{{ order.buyerRef }}
              </div>
              <div class="mb-2">
                {{ t('orders.warehouse') }}：{{ order.shipment.warehouse }}
              </div>
              <div class="mb-2">
                {{ t('orders.carrier') }}：{{ order.shipment.carrier }}
              </div>
              <div class="mb-2">
                {{ t('orders.tracking') }}：{{ order.shipment.trackingNo }}
              </div>
              <div>{{ order.fulfillment }} · {{ order.shipment.shippedAt }}</div>
            </VCardText>
          </VWindowItem>
        </VWindow>
      </VCard>
    </DetailPage>
  </div>
</template>
