<script setup lang="ts">
import { createBundle, deleteBundles, fetchBundles, fetchCatalogLookups, updateBundle } from '@/api/catalog'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useSessionStore } from '@/stores/session'
import type { BundleRow, LookupOption } from '@/types/domain'
import { numberText, requiredText } from '@/utils/form-rules'
import { can } from '@/utils/permission'

const { t } = useI18n({ useScope: 'global' })
const session = useSessionStore()
const { confirm } = useConfirm()
const rows = ref<BundleRow[]>([])
const skus = ref<LookupOption[]>([])
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const editingId = ref('')
const form = reactive({ parentInternalSku: '', childInternalSku: '', qty: '1' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [list, lookups] = await Promise.all([fetchBundles(), fetchCatalogLookups()])

    rows.value = list
    skus.value = lookups.skus
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loading.value = false
  }
}

onMounted(load)

const skuItems = computed(() => skus.value.map(item => item.label.split(' ')[0]))

const columns = computed(() => [
  { key: 'parentInternalSku', title: t('catalog.parentSku') },
  { key: 'parentTitle', title: t('catalog.name') },
  { key: 'childInternalSku', title: t('catalog.childSku') },
  { key: 'childTitle', title: t('catalog.name') },
  { key: 'qty', title: t('catalog.qty') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [{
  key: 'parentInternalSku',
  label: t('catalog.parentSku'),
  items: [...new Set(rows.value.map(item => item.parentInternalSku))].map(name => ({ title: name, value: name })),
}])

const batchActions = computed(() => can(session.role, 'delete')
  ? [{ key: 'delete', label: t('catalog.remove') }]
  : [])

function startCreate() {
  editingId.value = ''
  Object.assign(form, { parentInternalSku: skuItems.value[0] ?? '', childInternalSku: skuItems.value[1] ?? '', qty: '1' })
  open.value = true
}

function startEdit(row: BundleRow) {
  editingId.value = row.id
  Object.assign(form, { parentInternalSku: row.parentInternalSku, childInternalSku: row.childInternalSku, qty: String(row.qty) })
  open.value = true
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    const input = { parentInternalSku: form.parentInternalSku, childInternalSku: form.childInternalSku, qty: Number(form.qty) }

    if (editingId.value)
      await updateBundle(editingId.value, input)
    else
      await createBundle(input)

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

async function onBatch(_action: string, selected: BundleRow[]) {
  const ok = await confirm({
    title: t('catalog.remove'),
    text: selected.map(item => item.parentInternalSku).join(', '),
    confirmText: t('catalog.remove'),
    cancelText: t('foundation.cancel'),
  })

  if (!ok)
    return

  try {
    await deleteBundles(selected.map(item => item.id))
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
          {{ t('catalog.createBundle') }}
        </VBtn>
      </PermissionGate>
    </div>
    <ListPage
      storage-key="catalog-bundles"
      :title="t('catalog.bundleTitle')"
      :subtitle="t('catalog.bundleSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      :loading="loading"
      :error="error"
      :batch-actions="batchActions"
      @retry="load"
      @batch="onBatch"
    >
      <template #item.actions="{ item }">
        <PermissionGate action="update">
          <VBtn
            size="small"
            variant="text"
            @click="startEdit(item)"
          >
            {{ t('catalog.editBundle') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
    <FormDrawer
      v-model="open"
      :title="editingId ? t('catalog.editBundle') : t('catalog.createBundle')"
      :saving="saving"
      @save="save"
    >
      <AppAutocomplete
        v-model="form.parentInternalSku"
        :items="skuItems"
        :label="t('catalog.parentSku')"
        :rules="[requiredText(t('catalog.parentSku'))]"
        class="mb-4"
      />
      <AppAutocomplete
        v-model="form.childInternalSku"
        :items="skuItems"
        :label="t('catalog.childSku')"
        :rules="[requiredText(t('catalog.childSku'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.qty"
        :label="t('catalog.qty')"
        :rules="[requiredText(t('catalog.qty')), numberText(t('catalog.qty'))]"
      />
    </FormDrawer>
  </div>
</template>
