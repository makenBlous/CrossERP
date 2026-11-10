<script setup lang="ts">
import { createShipment, fetchShipments } from '@/api/logistics'
import { fetchSupplyLookups } from '@/api/procurement'
import { arriveShipment, departShipment } from '@/api/workflows'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useConfirm } from '@/composables/useConfirm'
import { usePageContext } from '@/composables/usePageContext'
import type { ShipmentRow, SupplyLookups } from '@/types/domain'
import { moneyText, numberText, requiredText } from '@core/utils/validators'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const { confirm } = useConfirm()
const { setSelected } = usePageContext()
const rows = ref<ShipmentRow[]>([])
const lookups = ref<SupplyLookups | null>(null)
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const acting = ref(false)

const form = reactive({
  carrierId: '',
  warehouseFrom: '',
  warehouseTo: '',
  internalSku: '',
  qty: '12',
  containerNo: '',
  volumetricKg: '',
  chargeAmount: '',
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchShipments()
    lookups.value = await fetchSupplyLookups()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loading.value = false
  }
}

onMounted(load)

const columns = computed(() => [
  { key: 'no', title: t('inventory.docNo') },
  { key: 'carrierName', title: t('logistics.carrier') },
  { key: 'fromName', title: t('logistics.from') },
  { key: 'toName', title: t('logistics.to') },
  { key: 'status', title: t('common.status') },
  { key: 'skuSummary', title: t('logistics.sku') },
  { key: 'departedAt', title: t('logistics.departed') },
  { key: 'arrivedAt', title: t('logistics.arrived') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [{
  key: 'status',
  label: t('common.status'),
  items: [...new Set(rows.value.map(item => item.status))].map(name => ({ title: name, value: name })),
}])

function startCreate() {
  const warehouses = lookups.value?.warehouses ?? []

  form.carrierId = lookups.value?.carriers[0]?.id ?? ''
  form.warehouseFrom = warehouses.find(item => item.id === 'wh-cn-sz')?.id ?? warehouses[0]?.id ?? ''
  form.warehouseTo = warehouses.find(item => item.id === 'wh-fba-us')?.id ?? warehouses[1]?.id ?? ''
  form.internalSku = lookups.value?.skus[0]?.id ?? ''
  form.qty = '12'
  form.containerNo = ''
  form.volumetricKg = ''
  form.chargeAmount = ''
  open.value = true
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    const created = await createShipment({
      ...form,
      qty: Number.parseInt(form.qty, 10),
    })

    open.value = false
    await load()
    await router.push({ path: `/logistics/shipments/${created.id}` })
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    saving.value = false
  }
}

async function act(row: ShipmentRow, kind: 'ship' | 'receive') {
  const ok = await confirm({
    title: kind === 'ship' ? t('logistics.ship') : t('logistics.receive'),
    text: row.no,
    confirmText: kind === 'ship' ? t('logistics.ship') : t('logistics.receive'),
    cancelText: t('foundation.cancel'),
  })

  if (!ok)
    return

  acting.value = true
  message.value = ''
  try {
    setSelected(row.id)
    if (kind === 'ship')
      await departShipment(row.id)
    else
      await arriveShipment(row.id)

    await load()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    acting.value = false
  }
}

function openRow(row: ShipmentRow) {
  setSelected(row.id)
  router.push({ path: `/logistics/shipments/${row.id}` })
}
</script>

<template>
  <div>
    <VAlert
      v-if="message"
      type="warning"
      variant="tonal"
      class="mb-4"
    >
      {{ message }}
    </VAlert>
    <ListPage
      storage-key="logistics-first-mile"
      :title="t('logistics.firstMileTitle')"
      :subtitle="t('logistics.firstMileSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      date-key="departedAt"
      :loading="loading"
      :error="error"
      @retry="load"
      @open="openRow"
    >
      <template #actions>
        <PermissionGate action="create">
          <VBtn
            color="primary"
            @click="startCreate"
          >
            {{ t('logistics.createPlan') }}
          </VBtn>
        </PermissionGate>
      </template>
      <template #item.status="{ item }">
        <StatusChip
          domain="shipment"
          :value="item.status"
        />
      </template>
      <template #item.actions="{ item }">
        <VBtn
          size="small"
          variant="text"
          :to="{ path: `/logistics/shipments/${item.id}` }"
        >
          {{ t('common.view') }}
        </VBtn>
        <PermissionGate action="ship">
          <VBtn
            v-if="item.status === 'planned'"
            size="small"
            variant="text"
            data-test="fm-ship"
            :loading="acting"
            @click="act(item, 'ship')"
          >
            {{ t('logistics.ship') }}
          </VBtn>
        </PermissionGate>
        <PermissionGate action="receive">
          <VBtn
            v-if="item.status === 'in_transit'"
            size="small"
            variant="text"
            data-test="fm-receive"
            :loading="acting"
            @click="act(item, 'receive')"
          >
            {{ t('logistics.receive') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
    <FormDrawer
      v-model="open"
      :title="t('logistics.createPlan')"
      :saving="saving"
      @save="save"
    >
      <AppSelect
        v-model="form.carrierId"
        :items="(lookups?.carriers ?? []).map(item => ({ title: item.label, value: item.id }))"
        :label="t('logistics.carrier')"
        :rules="[requiredText(t('logistics.carrier'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="form.warehouseFrom"
        :items="(lookups?.warehouses ?? []).map(item => ({ title: item.label, value: item.id }))"
        :label="t('logistics.from')"
        :rules="[requiredText(t('logistics.from'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="form.warehouseTo"
        :items="(lookups?.warehouses ?? []).map(item => ({ title: item.label, value: item.id }))"
        :label="t('logistics.to')"
        :rules="[requiredText(t('logistics.to'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="form.internalSku"
        :items="(lookups?.skus ?? []).map(item => ({ title: item.label, value: item.id }))"
        :label="t('logistics.sku')"
        :rules="[requiredText(t('logistics.sku'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.qty"
        :label="t('logistics.qty')"
        :rules="[requiredText(t('logistics.qty')), numberText(t('logistics.qty'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.containerNo"
        :label="t('logistics.container')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.volumetricKg"
        :label="t('logistics.volumetric')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.chargeAmount"
        :label="t('logistics.feeAmount')"
        :rules="[moneyText(t('logistics.feeAmount'))]"
      />
    </FormDrawer>
  </div>
</template>
