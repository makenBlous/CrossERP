<script setup lang="ts">
import { changeWarehouseActive, createWarehouse, fetchWarehouses, updateWarehouse } from '@/api/inventory'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useSessionStore } from '@/stores/session'
import type { WarehouseRow } from '@/types/domain'
import { requiredText } from '@core/utils/validators'
import { can } from '@/utils/permission'

const { t } = useI18n({ useScope: 'global' })
const session = useSessionStore()
const { confirm } = useConfirm()
const rows = ref<WarehouseRow[]>([])
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const editingId = ref('')
const form = reactive({ code: '', name: '', kind: 'domestic', country: 'CN' })

const kinds = computed(() => [
  { title: t('inventory.kindFba'), value: 'fba' },
  { title: t('inventory.kindOverseas'), value: 'overseas' },
  { title: t('inventory.kindDomestic'), value: 'domestic' },
])

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchWarehouses()
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
  { key: 'code', title: t('inventory.code') },
  { key: 'name', title: t('inventory.name') },
  { key: 'kind', title: t('inventory.kind') },
  { key: 'country', title: t('inventory.country') },
  { key: 'status', title: t('common.status') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [
  { key: 'kind', label: t('inventory.kind'), items: kinds.value },
  {
    key: 'status',
    label: t('common.status'),
    items: [
      { title: t('inventory.enable'), value: 'active' },
      { title: t('inventory.disable'), value: 'disabled' },
    ],
  },
])

const batchActions = computed(() => can(session.role, 'update')
  ? [{ key: 'enable', label: t('inventory.enable') }, { key: 'disable', label: t('inventory.disable') }]
  : [])

function startCreate() {
  editingId.value = ''
  form.code = ''
  form.name = ''
  form.kind = 'domestic'
  form.country = 'CN'
  open.value = true
}

function startEdit(row: WarehouseRow) {
  editingId.value = row.id
  form.code = row.code
  form.name = row.name
  form.kind = row.kind
  form.country = row.country
  open.value = true
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    const payload = { code: form.code, name: form.name, kind: form.kind as 'fba' | 'overseas' | 'domestic', country: form.country }

    if (editingId.value)
      await updateWarehouse(editingId.value, payload)
    else
      await createWarehouse(payload)

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

async function onBatch(action: string, selected: WarehouseRow[]) {
  if (action === 'disable') {
    const ok = await confirm({
      title: t('inventory.disable'),
      text: selected.map(item => item.name).join(', '),
      confirmText: t('inventory.disable'),
      cancelText: t('foundation.cancel'),
    })

    if (!ok)
      return
  }

  try {
    await changeWarehouseActive(selected.map(item => item.id), action === 'enable')
    await load()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}
</script>

<template>
  <div>
    <VAlert
      v-if="message"
      type="error"
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
          {{ t('inventory.createWarehouse') }}
        </VBtn>
      </PermissionGate>
    </div>
    <ListPage
      storage-key="inventory-warehouses"
      :title="t('inventory.warehousesTitle')"
      :subtitle="t('inventory.warehousesSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      :loading="loading"
      :error="error"
      :batch-actions="batchActions"
      @retry="load"
      @batch="onBatch"
    >
      <template #item.kind="{ item }">
        {{ item.kind === 'fba' ? t('inventory.kindFba') : item.kind === 'overseas' ? t('inventory.kindOverseas') : t('inventory.kindDomestic') }}
      </template>
      <template #item.status="{ item }">
        <StatusChip
          domain="generic"
          :value="item.status"
        />
      </template>
      <template #item.actions="{ item }">
        <PermissionGate action="update">
          <VBtn
            size="small"
            variant="text"
            @click="startEdit(item)"
          >
            {{ t('inventory.editWarehouse') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
    <FormDrawer
      v-model="open"
      :title="editingId ? t('inventory.editWarehouse') : t('inventory.createWarehouse')"
      :saving="saving"
      @save="save"
    >
      <AppTextField
        v-model="form.code"
        :label="t('inventory.code')"
        :rules="[requiredText(t('inventory.code'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.name"
        :label="t('inventory.name')"
        :rules="[requiredText(t('inventory.name'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="form.kind"
        :items="kinds"
        :label="t('inventory.kind')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.country"
        :label="t('inventory.country')"
        :rules="[requiredText(t('inventory.country'))]"
      />
    </FormDrawer>
  </div>
</template>
