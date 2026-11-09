<script setup lang="ts">
import { changeCarrierActive, createCarrier, fetchCarriers, updateCarrier } from '@/api/logistics'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useSessionStore } from '@/stores/session'
import type { CarrierRow } from '@/types/domain'
import { requiredText } from '@core/utils/validators'
import { can } from '@/utils/permission'

const { t } = useI18n({ useScope: 'global' })
const session = useSessionStore()
const { confirm } = useConfirm()
const rows = ref<CarrierRow[]>([])
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const editingId = ref('')
const name = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchCarriers()
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
  { key: 'name', title: t('logistics.carrier') },
  { key: 'rateCount', title: t('logistics.ratesTitle'), align: 'end' as const },
  { key: 'status', title: t('common.status') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [{
  key: 'status',
  label: t('common.status'),
  items: [
    { title: t('inventory.enable'), value: 'active' },
    { title: t('inventory.disable'), value: 'disabled' },
  ],
}])

const batchActions = computed(() => can(session.role, 'update')
  ? [{ key: 'enable', label: t('inventory.enable') }, { key: 'disable', label: t('inventory.disable') }]
  : [])

function startCreate() {
  editingId.value = ''
  name.value = ''
  open.value = true
}

function startEdit(row: CarrierRow) {
  editingId.value = row.id
  name.value = row.name
  open.value = true
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    if (editingId.value)
      await updateCarrier(editingId.value, { name: name.value })
    else
      await createCarrier({ name: name.value })

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

async function onBatch(action: string, selected: CarrierRow[]) {
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
    await changeCarrierActive(selected.map(item => item.id), action === 'enable')
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
          {{ t('logistics.createCarrier') }}
        </VBtn>
      </PermissionGate>
    </div>
    <ListPage
      storage-key="logistics-carriers"
      :title="t('logistics.carriersTitle')"
      :subtitle="t('logistics.carriersSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      :loading="loading"
      :error="error"
      :batch-actions="batchActions"
      @retry="load"
      @batch="onBatch"
    >
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
            {{ t('logistics.editCarrier') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
    <FormDrawer
      v-model="open"
      :title="editingId ? t('logistics.editCarrier') : t('logistics.createCarrier')"
      :saving="saving"
      @save="save"
    >
      <AppTextField
        v-model="name"
        :label="t('logistics.carrier')"
        :rules="[requiredText(t('logistics.carrier'))]"
      />
    </FormDrawer>
  </div>
</template>
