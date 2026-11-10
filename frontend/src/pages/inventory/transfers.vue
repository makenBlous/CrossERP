<script setup lang="ts">
import { confirmTransfer, createStockDoc, fetchStockDoc, fetchStockDocs } from '@/api/inventory'
import { fetchSupplyLookups } from '@/api/procurement'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import RecordDrawer from '@/components/biz/RecordDrawer.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useConfirm } from '@/composables/useConfirm'
import type { StockDocDetail, StockDocRow, SupplyLookups } from '@/types/domain'
import { numberText, requiredText } from '@core/utils/validators'
import GapBPage from '@/views/gap-b/GapBPage.vue'

const route = useRoute()
const isGapBDetail = computed(() => route.path !== '/inventory/transfers')

const { t } = useI18n({ useScope: 'global' })
const { confirm } = useConfirm()
const rows = ref<StockDocRow[]>([])
const lookups = ref<SupplyLookups | null>(null)
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const drawer = ref(false)
const detail = ref<StockDocDetail | null>(null)
const form = reactive({ warehouseId: '', toWarehouseId: '', internalSku: '', qty: '1', remark: '' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchStockDocs('transfer')
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
  { key: 'docNo', title: t('inventory.docNo') },
  { key: 'warehouseName', title: t('inventory.fromWarehouse') },
  { key: 'toWarehouseName', title: t('inventory.toWarehouse') },
  { key: 'lineSummary', title: t('inventory.sku') },
  { key: 'status', title: t('common.status') },
  { key: 'createdAt', title: t('orders.date') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [{
  key: 'status',
  label: t('common.status'),
  items: [...new Set(rows.value.map(item => item.status))].map(name => ({ title: name, value: name })),
}])

const warehouseItems = computed(() => (lookups.value?.warehouses ?? []).map(item => ({ title: item.label, value: item.id })))

async function openRow(row: StockDocRow) {
  detail.value = await fetchStockDoc(row.id)
  drawer.value = true
}

function startCreate() {
  const warehouses = lookups.value?.warehouses ?? []

  form.warehouseId = warehouses[0]?.id ?? ''
  form.toWarehouseId = warehouses[1]?.id ?? ''
  form.internalSku = lookups.value?.skus[0]?.id ?? ''
  form.qty = '1'
  form.remark = ''
  open.value = true
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    await createStockDoc({
      docType: 'transfer',
      warehouseId: form.warehouseId,
      toWarehouseId: form.toWarehouseId,
      internalSku: form.internalSku,
      qty: Number.parseInt(form.qty, 10),
      remark: form.remark,
    })
    open.value = false
    await load()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    saving.value = false
  }
}

async function confirmRow(row: StockDocRow) {
  const ok = await confirm({
    title: t('inventory.confirmTransfer'),
    text: row.docNo,
    confirmText: t('inventory.confirmTransfer'),
    cancelText: t('foundation.cancel'),
  })

  if (!ok)
    return

  try {
    await confirmTransfer(row.id)
    drawer.value = false
    await load()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}
</script>

<template>
  <GapBPage
    v-if="isGapBDetail"
    page-key="I14"
  />
  <div v-else>
    <VAlert
      v-if="message"
      type="warning"
      variant="tonal"
      class="mb-4"
    >
      {{ message }}
    </VAlert>
    <ListPage
      storage-key="inventory-transfers"
      :title="t('inventory.transfersTitle')"
      :subtitle="t('inventory.transfersSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      date-key="createdAt"
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
            {{ t('inventory.createDoc') }}
          </VBtn>
        </PermissionGate>
      </template>
      <template #item.status="{ item }">
        <StatusChip
          domain="stock_doc"
          :value="item.status"
        />
      </template>
      <template #item.actions="{ item }">
        <VBtn
          size="small"
          variant="text"
          @click="openRow(item)"
        >
          {{ t('common.view') }}
        </VBtn>
        <PermissionGate action="update">
          <VBtn
            v-if="item.status === 'draft'"
            size="small"
            variant="text"
            @click="confirmRow(item)"
          >
            {{ t('inventory.confirmTransfer') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
    <RecordDrawer
      v-model="drawer"
      :title="detail?.docNo || t('inventory.transfersTitle')"
    >
      <template v-if="detail">
        <p>{{ detail.warehouseName }} → {{ detail.toWarehouseName }}</p>
        <p>{{ detail.remark }}</p>
        <div
          v-for="line in detail.lines"
          :key="line.id"
        >
          {{ line.internalSku }} × {{ line.qtyExpected }}
        </div>
      </template>
    </RecordDrawer>
    <FormDrawer
      v-model="open"
      :title="t('inventory.createDoc')"
      :saving="saving"
      @save="save"
    >
      <AppSelect
        v-model="form.warehouseId"
        :items="warehouseItems"
        :label="t('inventory.fromWarehouse')"
        :rules="[requiredText(t('inventory.fromWarehouse'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="form.toWarehouseId"
        :items="warehouseItems"
        :label="t('inventory.toWarehouse')"
        :rules="[requiredText(t('inventory.toWarehouse'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="form.internalSku"
        :items="(lookups?.skus ?? []).map(item => ({ title: item.label, value: item.id }))"
        :label="t('inventory.sku')"
        :rules="[requiredText(t('inventory.sku'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.qty"
        :label="t('inventory.qty')"
        :rules="[requiredText(t('inventory.qty')), numberText(t('inventory.qty'))]"
      />
    </FormDrawer>
  </div>
</template>
