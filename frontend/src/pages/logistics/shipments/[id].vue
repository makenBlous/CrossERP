<script setup lang="ts">
import { fetchShipment, saveShipmentFee } from '@/api/logistics'
import { arriveShipment, departShipment } from '@/api/workflows'
import DetailPage from '@/components/biz/DetailPage.vue'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import { useConfirm } from '@/composables/useConfirm'
import { usePageContext } from '@/composables/usePageContext'
import type { CurrencyCode, ShipmentDetailView } from '@/types/domain'
import { moneyText, requiredText } from '@core/utils/validators'
import { readParam } from '@/utils/route-param'

const route = useRoute()
const { t } = useI18n({ useScope: 'global' })
const { confirm } = useConfirm()
const { setSelected } = usePageContext()
const shipment = ref<ShipmentDetailView | null>(null)
const loaded = ref(false)
const acting = ref(false)
const error = ref('')
const tab = ref('route')
const feeOpen = ref(false)
const saving = ref(false)

const fee = reactive({
  chargeType: 'freight',
  amount: '',
  currency: 'CNY' as CurrencyCode,
  containerNo: '',
  volumetricKg: '',
})

const shipmentId = computed(() => readParam(route.params, 'id'))
const currencies = ['USD', 'CNY', 'EUR', 'GBP', 'JPY'].map(item => ({ title: item, value: item }))

async function load() {
  loaded.value = false
  error.value = ''
  try {
    shipment.value = await fetchShipment(shipmentId.value)
    if (shipment.value) {
      fee.containerNo = shipment.value.containerNo
      fee.volumetricKg = shipment.value.volumetricKg
    }
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loaded.value = true
  }
}

onMounted(load)
watch(shipmentId, load)
watch(shipment, value => setSelected(value?.id ?? null))
onUnmounted(() => setSelected(null))

async function act(kind: 'ship' | 'receive') {
  if (!shipment.value)
    return

  const ok = await confirm({
    title: kind === 'ship' ? t('logistics.ship') : t('logistics.receive'),
    text: shipment.value.no,
    confirmText: kind === 'ship' ? t('logistics.ship') : t('logistics.receive'),
    cancelText: t('foundation.cancel'),
  })

  if (!ok)
    return

  acting.value = true
  error.value = ''
  try {
    if (kind === 'ship')
      await departShipment(shipment.value.id)
    else
      await arriveShipment(shipment.value.id)

    await load()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    acting.value = false
  }
}

async function saveFee() {
  if (!shipment.value)
    return

  saving.value = true
  error.value = ''
  try {
    await saveShipmentFee({
      shipmentId: shipment.value.id,
      chargeType: fee.chargeType,
      amount: fee.amount,
      currency: fee.currency,
      containerNo: fee.containerNo,
      volumetricKg: fee.volumetricKg,
    })
    feeOpen.value = false
    await load()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <VBtn
      variant="text"
      class="mb-4"
      prepend-icon="tabler-arrow-left"
      :to="{ path: '/logistics/first-mile' }"
    >
      {{ t('logistics.firstMileTitle') }}
    </VBtn>
    <ErrorState
      v-if="error"
      class="mb-4"
      :text="error"
      @retry="load"
    />
    <LoadingState v-if="!loaded" />
    <VAlert
      v-else-if="!shipment"
      type="warning"
      variant="tonal"
    >
      {{ t('logistics.shipmentMissing') }}
    </VAlert>
    <DetailPage
      v-else
      :title="shipment.no"
      :subtitle="`${shipment.fromName} → ${shipment.toName}`"
      domain="shipment"
      :status="shipment.status"
      :timeline="shipment.timeline"
      :related="shipment.related"
    >
      <template #actions>
        <PermissionGate action="ship">
          <VBtn
            v-if="shipment.status === 'planned'"
            color="primary"
            data-test="fm-ship"
            :loading="acting"
            @click="act('ship')"
          >
            {{ t('logistics.ship') }}
          </VBtn>
        </PermissionGate>
        <PermissionGate action="receive">
          <VBtn
            v-if="shipment.status === 'in_transit'"
            color="primary"
            data-test="fm-receive"
            :loading="acting"
            @click="act('receive')"
          >
            {{ t('logistics.receive') }}
          </VBtn>
        </PermissionGate>
        <PermissionGate action="update">
          <VBtn
            variant="tonal"
            @click="feeOpen = true"
          >
            {{ t('logistics.saveFee') }}
          </VBtn>
        </PermissionGate>
      </template>
      <VTabs
        v-model="tab"
        class="v-tabs-pill mb-6"
      >
        <VTab value="route">
          {{ t('logistics.detailRoute') }}
        </VTab>
        <VTab value="cartons">
          {{ t('logistics.cartons') }}
        </VTab>
        <VTab value="fees">
          {{ t('logistics.fees') }}
        </VTab>
        <VTab value="tracking">
          {{ t('logistics.tracking') }}
        </VTab>
      </VTabs>
      <VWindow
        v-model="tab"
        class="disable-tab-transition"
        :touch="false"
      >
        <VWindowItem value="route">
          <VCard>
            <VCardText>
              <div class="mb-2">
                {{ t('logistics.carrier') }}：{{ shipment.carrierName }}
              </div>
              <div class="mb-2">
                {{ t('logistics.container') }}：{{ shipment.containerNo || '—' }}
              </div>
              <div class="mb-2">
                {{ t('logistics.volumetric') }}：{{ shipment.volumetricKg || '—' }}
              </div>
              <div>{{ t('logistics.departed') }}：{{ shipment.departedAt || '—' }}</div>
              <div>{{ t('logistics.arrived') }}：{{ shipment.arrivedAt || '—' }}</div>
            </VCardText>
          </VCard>
        </VWindowItem>
        <VWindowItem value="cartons">
          <VCard>
            <VTable>
              <thead>
                <tr>
                  <th>{{ t('logistics.sku') }}</th>
                  <th class="text-end">
                    {{ t('logistics.qty') }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="line in shipment.lines"
                  :key="line.id"
                >
                  <td>{{ line.internalSku }}</td>
                  <td class="text-end">
                    {{ line.qty }}
                  </td>
                </tr>
              </tbody>
            </VTable>
          </VCard>
        </VWindowItem>
        <VWindowItem value="fees">
          <VCard>
            <VCardText>
              {{ t('logistics.feeHint') }}
            </VCardText>
            <VTable>
              <thead>
                <tr>
                  <th>{{ t('logistics.feeType') }}</th>
                  <th class="text-end">
                    {{ t('logistics.feeAmount') }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in shipment.charges"
                  :key="item.id"
                >
                  <td>{{ item.chargeType }}</td>
                  <td class="text-end">
                    <MoneyText
                      :amount="item.amount"
                      :currency="item.currency"
                    />
                  </td>
                </tr>
              </tbody>
            </VTable>
          </VCard>
        </VWindowItem>
        <VWindowItem value="tracking">
          <VCard>
            <VCardText>
              <VTimeline
                v-if="shipment.tracking.length"
                density="compact"
                align="start"
              >
                <VTimelineItem
                  v-for="item in shipment.tracking"
                  :key="item.id"
                  dot-color="primary"
                  size="x-small"
                >
                  <div class="text-caption text-disabled">
                    {{ item.occurredAt }}
                  </div>
                  <div>{{ item.description }}</div>
                </VTimelineItem>
              </VTimeline>
              <EmptyState
                v-else
                :text="t('foundation.noTimeline')"
              />
            </VCardText>
          </VCard>
        </VWindowItem>
      </VWindow>
    </DetailPage>
    <FormDrawer
      v-model="feeOpen"
      :title="t('logistics.saveFee')"
      :saving="saving"
      @save="saveFee"
    >
      <AppTextField
        v-model="fee.containerNo"
        :label="t('logistics.container')"
        class="mb-4"
      />
      <AppTextField
        v-model="fee.volumetricKg"
        :label="t('logistics.volumetric')"
        class="mb-4"
      />
      <AppTextField
        v-model="fee.chargeType"
        :label="t('logistics.feeType')"
        :rules="[requiredText(t('logistics.feeType'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="fee.amount"
        :label="t('logistics.feeAmount')"
        :rules="[requiredText(t('logistics.feeAmount')), moneyText(t('logistics.feeAmount'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="fee.currency"
        :items="currencies"
        :label="t('procurement.currency')"
      />
    </FormDrawer>
  </div>
</template>
