<script setup lang="ts">
import { cancelPurchaseOrder, fetchPurchaseOrder, fetchSupplyLookups } from '@/api/procurement'
import { approvePurchaseOrder, receivePurchaseOrder, rejectPurchaseOrder, submitPurchaseOrder } from '@/api/workflows'
import DetailPage from '@/components/biz/DetailPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import { useConfirm } from '@/composables/useConfirm'
import { usePageContext } from '@/composables/usePageContext'
import type { PurchaseOrderDetailView, SupplyLookups } from '@/types/domain'
import { readParam } from '@/utils/route-param'

const route = useRoute()
const { t } = useI18n({ useScope: 'global' })
const { confirm } = useConfirm()
const { setSelected } = usePageContext()
const order = ref<PurchaseOrderDetailView | null>(null)
const lookups = ref<SupplyLookups | null>(null)
const loaded = ref(false)
const acting = ref(false)
const error = ref('')
const tab = ref('lines')
const warehouseId = ref('')

const orderId = computed(() => readParam(route.params, 'id'))

async function load() {
  loaded.value = false
  error.value = ''
  try {
    order.value = await fetchPurchaseOrder(orderId.value)
    lookups.value = await fetchSupplyLookups()
    if (!warehouseId.value)
      warehouseId.value = lookups.value.warehouses.find(item => item.id === 'wh-cn-sz')?.id ?? lookups.value.warehouses[0]?.id ?? ''
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

async function run(action: () => Promise<unknown>) {
  acting.value = true
  error.value = ''
  try {
    await action()
    await load()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    acting.value = false
  }
}

async function receive() {
  if (!order.value)
    return

  const ok = await confirm({
    title: t('procurement.receive'),
    text: order.value.no,
    confirmText: t('procurement.receive'),
    cancelText: t('foundation.cancel'),
  })

  if (!ok)
    return

  const current = order.value

  if (!current)
    return

  await run(() => receivePurchaseOrder(current.id, warehouseId.value))
}

function submitCurrent() {
  const current = order.value

  if (current)
    return run(() => submitPurchaseOrder(current.id))
}

function approveCurrent() {
  const current = order.value

  if (current)
    return run(() => approvePurchaseOrder(current.id))
}

function rejectCurrent() {
  const current = order.value

  if (current)
    return run(() => rejectPurchaseOrder(current.id))
}

async function cancel() {
  if (!order.value)
    return

  const ok = await confirm({
    title: t('procurement.cancel'),
    text: order.value.no,
    confirmText: t('procurement.cancel'),
    cancelText: t('foundation.cancel'),
  })

  if (!ok)
    return

  const current = order.value

  if (!current)
    return

  await run(() => cancelPurchaseOrder(current.id))
}
</script>

<template>
  <div>
    <VBtn
      variant="text"
      class="mb-4"
      prepend-icon="tabler-arrow-left"
      :to="{ path: '/procurement/orders' }"
    >
      {{ t('procurement.ordersTitle') }}
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
      {{ t('procurement.poMissing') }}
    </VAlert>
    <DetailPage
      v-else
      :title="order.no"
      :subtitle="`${order.supplierName} · ${order.expectedAt}`"
      domain="purchase_order"
      :status="order.status"
      :timeline="order.timeline"
      :related="order.related"
    >
      <template #actions>
        <PermissionGate action="update">
          <VBtn
            v-if="order.status === 'draft'"
            :loading="acting"
            @click="submitCurrent"
          >
            {{ t('procurement.submit') }}
          </VBtn>
        </PermissionGate>
        <PermissionGate action="approve">
          <VBtn
            v-if="order.status === 'submitted'"
            color="success"
            data-test="po-approve"
            :loading="acting"
            @click="approveCurrent"
          >
            {{ t('procurement.approve') }}
          </VBtn>
          <VBtn
            v-if="order.status === 'submitted'"
            color="error"
            variant="tonal"
            :loading="acting"
            @click="rejectCurrent"
          >
            {{ t('procurement.reject') }}
          </VBtn>
        </PermissionGate>
        <PermissionGate action="receive">
          <AppSelect
            v-if="order.status === 'approved' || order.status === 'partial'"
            v-model="warehouseId"
            :items="(lookups?.warehouses ?? []).map(item => ({ title: item.label, value: item.id }))"
            :label="t('procurement.receiveWarehouse')"
            style="min-width: 220px"
          />
          <VBtn
            v-if="order.status === 'approved' || order.status === 'partial'"
            color="primary"
            data-test="po-receive"
            :loading="acting"
            @click="receive"
          >
            {{ t('procurement.receive') }}
          </VBtn>
        </PermissionGate>
        <PermissionGate action="update">
          <VBtn
            v-if="order.status === 'draft' || order.status === 'rejected'"
            variant="tonal"
            color="secondary"
            :loading="acting"
            @click="cancel"
          >
            {{ t('procurement.cancel') }}
          </VBtn>
        </PermissionGate>
      </template>

      <VTabs
        v-model="tab"
        class="v-tabs-pill mb-6"
      >
        <VTab value="lines">
          {{ t('procurement.detailLines') }}
        </VTab>
        <VTab value="receipts">
          {{ t('procurement.receipts') }}
        </VTab>
        <VTab value="files">
          {{ t('procurement.attachments') }}
        </VTab>
      </VTabs>
      <VWindow
        v-model="tab"
        class="disable-tab-transition"
        :touch="false"
      >
        <VWindowItem value="lines">
          <VCard>
            <VTable>
              <thead>
                <tr>
                  <th>{{ t('inventory.sku') }}</th>
                  <th class="text-end">
                    {{ t('inventory.qty') }}
                  </th>
                  <th class="text-end">
                    {{ t('procurement.receivedQty') }}
                  </th>
                  <th class="text-end">
                    {{ t('procurement.unitCost') }}
                  </th>
                  <th class="text-end">
                    {{ t('procurement.amount') }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="line in order.lines"
                  :key="line.id"
                >
                  <td>{{ line.internalSku }}</td>
                  <td class="text-end">
                    {{ line.qty }}
                  </td>
                  <td class="text-end">
                    {{ line.receivedQty }}
                  </td>
                  <td class="text-end">
                    <MoneyText
                      :amount="line.unitCost"
                      :currency="line.currency"
                    />
                  </td>
                  <td class="text-end">
                    <MoneyText
                      :amount="line.amount"
                      :currency="line.currency"
                    />
                  </td>
                </tr>
              </tbody>
            </VTable>
          </VCard>
        </VWindowItem>
        <VWindowItem value="receipts">
          <VCard>
            <VTable>
              <thead>
                <tr>
                  <th>{{ t('inventory.docNo') }}</th>
                  <th>{{ t('inventory.warehouse') }}</th>
                  <th>{{ t('orders.date') }}</th>
                  <th class="text-end">
                    {{ t('procurement.receivedQty') }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in order.receipts"
                  :key="item.id"
                >
                  <td>{{ item.no }}</td>
                  <td>{{ item.warehouseName }}</td>
                  <td>{{ item.receivedAt }}</td>
                  <td class="text-end">
                    {{ item.qty }}
                  </td>
                </tr>
              </tbody>
            </VTable>
            <VCardText v-if="order.receipts.length === 0">
              <EmptyState :text="t('foundation.emptyText')" />
            </VCardText>
          </VCard>
        </VWindowItem>
        <VWindowItem value="files">
          <VCard>
            <VCardText>
              <EmptyState :text="t('procurement.noAttachment')" />
            </VCardText>
          </VCard>
        </VWindowItem>
      </VWindow>
    </DetailPage>
  </div>
</template>
