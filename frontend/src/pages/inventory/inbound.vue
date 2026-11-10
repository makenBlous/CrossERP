<script setup lang="ts">
import { completeStockDoc, createStockDoc, fetchStockDoc, fetchStockDocs } from '@/api/inventory'
import { fetchSupplyLookups } from '@/api/procurement'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import RecordDrawer from '@/components/biz/RecordDrawer.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useSessionStore } from '@/stores/session'
import type { StockDocDetail, StockDocRow, SupplyLookups } from '@/types/domain'
import { numberText, requiredText } from '@core/utils/validators'
import { can } from '@/utils/permission'

const { t } = useI18n({ useScope: 'global' })
const session = useSessionStore()
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
const form = reactive({ warehouseId: '', internalSku: '', qty: '1', remark: '' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchStockDocs('inbound')
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
  { key: 'warehouseName', title: t('inventory.warehouse') },
  { key: 'lineSummary', title: t('inventory.sku') },
  { key: 'status', title: t('common.status') },
  { key: 'createdAt', title: t('orders.date') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [
  {
    key: 'warehouseName',
    label: t('inventory.warehouse'),
    items: [...new Set(rows.value.map(item => item.warehouseName))].map(name => ({ title: name, value: name })),
  },
  {
    key: 'status',
    label: t('common.status'),
    items: [...new Set(rows.value.map(item => item.status))].map(name => ({ title: name, value: name })),
  },
])

const batchActions = computed(() => can(session.role, 'update')
  ? [{ key: 'post', label: t('inventory.completeDoc') }]
  : [])

async function openRow(row: StockDocRow) {
  detail.value = await fetchStockDoc(row.id)
  drawer.value = true
}

function startCreate() {
  form.warehouseId = lookups.value?.warehouses[0]?.id ?? ''
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
      docType: 'inbound',
      warehouseId: form.warehouseId,
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

async function complete(row: StockDocRow) {
  const ok = await confirm({
    title: t('inventory.completeDoc'),
    text: row.docNo,
    confirmText: t('inventory.completeDoc'),
    cancelText: t('foundation.cancel'),
  })

  if (!ok)
    return

  try {
    await completeStockDoc(row.id)
    drawer.value = false
    await load()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}

async function onBatch(_action: string, selected: StockDocRow[]) {
  for (const row of selected.filter(item => item.status === 'draft'))
    await complete(row)
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
      storage-key="inventory-inbound"
      :title="t('inventory.inboundTitle')"
      :subtitle="t('inventory.inboundSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      date-key="createdAt"
      :loading="loading"
      :error="error"
      :batch-actions="batchActions"
      @retry="load"
      @open="openRow"
      @batch="onBatch"
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
            @click="complete(item)"
          >
            {{ t('inventory.completeDoc') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
    <RecordDrawer
      v-model="drawer"
      :title="detail?.docNo || t('inventory.inboundTitle')"
    >
      <template v-if="detail">
        <p>{{ detail.warehouseName }} · {{ detail.remark }}</p>
        <VTable density="compact">
          <thead>
            <tr>
              <th>{{ t('inventory.sku') }}</th>
              <th class="text-end">
                {{ t('inventory.qty') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="line in detail.lines"
              :key="line.id"
            >
              <td>{{ line.internalSku }}</td>
              <td class="text-end">
                {{ line.qtyExpected }}
              </td>
            </tr>
          </tbody>
        </VTable>
        <div
          v-for="item in detail.timeline"
          :key="item.id"
          class="text-caption mt-3"
        >
          {{ item.at }} {{ item.actor }} {{ item.detail }}
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
        :items="(lookups?.warehouses ?? []).map(item => ({ title: item.label, value: item.id }))"
        :label="t('inventory.warehouse')"
        :rules="[requiredText(t('inventory.warehouse'))]"
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
        class="mb-4"
      />
      <AppTextField
        v-model="form.remark"
        :label="t('inventory.remark')"
      />
    </FormDrawer>
  </div>
</template>
