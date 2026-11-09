<script setup lang="ts">
import { createStockDoc, fetchStockDoc, fetchStockDocs, postStockCount } from '@/api/inventory'
import { fetchSupplyLookups } from '@/api/procurement'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import RecordDrawer from '@/components/biz/RecordDrawer.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import type { StockDocDetail, StockDocRow, SupplyLookups } from '@/types/domain'
import { numberText, requiredText } from '@core/utils/validators'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<StockDocRow[]>([])
const lookups = ref<SupplyLookups | null>(null)
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const posting = ref(false)
const drawer = ref(false)
const detail = ref<StockDocDetail | null>(null)
const actuals = reactive<Record<string, string>>({})
const form = reactive({ warehouseId: '', internalSku: '', qtyActual: '0', remark: '' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchStockDocs('count')
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

const filters = computed(() => [{
  key: 'status',
  label: t('common.status'),
  items: [...new Set(rows.value.map(item => item.status))].map(name => ({ title: name, value: name })),
}])

async function openRow(row: StockDocRow) {
  const found = await fetchStockDoc(row.id)

  detail.value = found
  for (const line of found?.lines ?? [])
    actuals[line.id] = String(found?.status === 'draft' ? line.bookQty : line.qtyActual)

  drawer.value = true
}

function startCreate() {
  form.warehouseId = lookups.value?.warehouses[0]?.id ?? ''
  form.internalSku = lookups.value?.skus[0]?.id ?? ''
  form.qtyActual = '0'
  form.remark = ''
  open.value = true
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    await createStockDoc({
      docType: 'count',
      warehouseId: form.warehouseId,
      internalSku: form.internalSku,
      qty: 1,
      qtyActual: Number.parseInt(form.qtyActual, 10),
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

function postCurrent() {
  return post()
}

async function post(row?: StockDocRow) {
  const target = row ?? rows.value.find(item => item.id === detail.value?.id)

  if (!target)
    return

  if (!detail.value || detail.value.id !== target.id)
    await openRow(target)

  posting.value = true
  message.value = ''
  try {
    await postStockCount(
      target.id,
      (detail.value?.lines ?? []).map(line => ({
        lineId: line.id,
        qtyActual: Number.parseInt(actuals[line.id] ?? String(line.qtyActual), 10),
      })),
    )
    drawer.value = false
    await load()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    posting.value = false
  }
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
    <div class="d-flex justify-end mb-4">
      <PermissionGate action="create">
        <VBtn
          color="primary"
          @click="startCreate"
        >
          {{ t('inventory.createDoc') }}
        </VBtn>
      </PermissionGate>
    </div>
    <ListPage
      storage-key="inventory-counts"
      :title="t('inventory.countsTitle')"
      :subtitle="t('inventory.countsSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      date-key="createdAt"
      :loading="loading"
      :error="error"
      @retry="load"
      @open="openRow"
    >
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
            data-test="count-post"
            :loading="posting"
            @click="post(item)"
          >
            {{ t('inventory.postCount') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
    <RecordDrawer
      v-model="drawer"
      :title="detail?.docNo || t('inventory.countsTitle')"
    >
      <template v-if="detail">
        <p class="mb-4">
          {{ detail.warehouseName }}
        </p>
        <div
          v-for="line in detail.lines"
          :key="line.id"
          class="mb-4"
        >
          <div class="text-body-2 mb-2">
            {{ line.internalSku }} · {{ t('inventory.bookQty') }} {{ line.bookQty }}
          </div>
          <AppTextField
            v-model="actuals[line.id]"
            :label="t('inventory.actualQty')"
            :disabled="detail.status !== 'draft'"
          />
        </div>
        <PermissionGate action="update">
          <VBtn
            v-if="detail.status === 'draft'"
            color="primary"
            data-test="count-post"
            :loading="posting"
            @click="postCurrent"
          >
            {{ t('inventory.postCount') }}
          </VBtn>
        </PermissionGate>
        <div
          v-for="item in detail.timeline"
          :key="item.id"
          class="text-caption mt-3"
        >
          {{ item.at }} {{ item.detail }}
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
        v-model="form.qtyActual"
        :label="t('inventory.actualQty')"
        :rules="[requiredText(t('inventory.actualQty')), numberText(t('inventory.actualQty'))]"
      />
    </FormDrawer>
  </div>
</template>
