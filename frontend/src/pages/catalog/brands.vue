<script setup lang="ts">
import { changeBrandActive, createBrand, fetchBrands, updateBrand } from '@/api/catalog'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useSessionStore } from '@/stores/session'
import type { BrandRow } from '@/types/domain'
import { requiredText } from '@core/utils/validators'
import { can } from '@/utils/permission'

const { t } = useI18n({ useScope: 'global' })
const session = useSessionStore()
const { confirm } = useConfirm()
const rows = ref<BrandRow[]>([])
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
    rows.value = await fetchBrands()
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
  { key: 'name', title: t('catalog.brand') },
  { key: 'skuCount', title: t('catalog.skuCount') },
  { key: 'status', title: t('common.status') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [{
  key: 'status',
  label: t('common.status'),
  items: [{ title: t('catalog.enable'), value: 'active' }, { title: t('catalog.disable'), value: 'disabled' }],
}])

const batchActions = computed(() => can(session.role, 'update')
  ? [{ key: 'enable', label: t('catalog.enable') }, { key: 'disable', label: t('catalog.disable') }]
  : [])

function startCreate() {
  editingId.value = ''
  name.value = ''
  open.value = true
}

function startEdit(row: BrandRow) {
  editingId.value = row.id
  name.value = row.name
  open.value = true
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    if (editingId.value)
      await updateBrand(editingId.value, { name: name.value })
    else
      await createBrand({ name: name.value })

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

async function onBatch(action: string, selected: BrandRow[]) {
  if (action === 'disable') {
    const ok = await confirm({
      title: t('catalog.disable'),
      text: selected.map(item => item.name).join(', '),
      confirmText: t('catalog.disable'),
      cancelText: t('foundation.cancel'),
    })

    if (!ok)
      return
  }

  try {
    await changeBrandActive(selected.map(item => item.id), action === 'enable')
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
    <ListPage
      storage-key="catalog-brands"
      :title="t('catalog.brandTitle')"
      :subtitle="t('catalog.brandSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      :loading="loading"
      :error="error"
      :batch-actions="batchActions"
      @retry="load"
      @batch="onBatch"
    >
      <template #actions>
        <PermissionGate action="create">
          <VBtn
            color="primary"
            @click="startCreate"
          >
            {{ t('catalog.createBrand') }}
          </VBtn>
        </PermissionGate>
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
            {{ t('catalog.editBrand') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
    <FormDrawer
      v-model="open"
      :title="editingId ? t('catalog.editBrand') : t('catalog.createBrand')"
      :saving="saving"
      @save="save"
    >
      <AppTextField
        v-model="name"
        :label="t('catalog.brand')"
        :rules="[requiredText(t('catalog.brand'))]"
      />
    </FormDrawer>
  </div>
</template>
