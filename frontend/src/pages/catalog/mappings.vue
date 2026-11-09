<script setup lang="ts">
import { confirmMappingRows, createMapping, fetchCatalogLookups, fetchMappings } from '@/api/catalog'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useSessionStore } from '@/stores/session'
import type { LookupOption, MappingRow } from '@/types/domain'
import { requiredText } from '@/utils/form-rules'
import { can } from '@/utils/permission'

const { t } = useI18n({ useScope: 'global' })
const session = useSessionStore()
const rows = ref<MappingRow[]>([])
const stores = ref<LookupOption[]>([])
const skus = ref<LookupOption[]>([])
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const form = reactive({ storeId: '', platformSku: '', internalSku: '', status: 'suggested' as 'confirmed' | 'suggested' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [list, lookups] = await Promise.all([fetchMappings(), fetchCatalogLookups()])

    rows.value = list
    stores.value = lookups.stores
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

const columns = computed(() => [
  { key: 'storeName', title: t('common.store') },
  { key: 'platform', title: t('orders.platform') },
  { key: 'platformSku', title: t('catalog.platformSku') },
  { key: 'internalSku', title: t('catalog.sku') },
  { key: 'status', title: t('common.status') },
])

const filters = computed(() => [
  { key: 'platform', label: t('orders.platform'), items: [...new Set(rows.value.map(item => item.platform))].map(name => ({ title: name, value: name })) },
  { key: 'status', label: t('common.status'), items: [{ title: t('catalog.confirm'), value: 'confirmed' }, { title: t('catalog.suggest'), value: 'suggested' }] },
])

const batchActions = computed(() => can(session.role, 'update')
  ? [{ key: 'confirm', label: t('catalog.confirm') }]
  : [])

function startCreate() {
  Object.assign(form, {
    storeId: stores.value[0]?.id ?? '',
    platformSku: '',
    internalSku: skus.value[0]?.label.split(' ')[0] ?? '',
    status: 'suggested' as const,
  })
  open.value = true
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    await createMapping({ ...form })
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

async function onBatch(action: string, selected: MappingRow[]) {
  if (action !== 'confirm')
    return

  try {
    await confirmMappingRows(selected.map(item => item.id))
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
          {{ t('catalog.createMapping') }}
        </VBtn>
      </PermissionGate>
    </div>
    <ListPage
      storage-key="catalog-mappings"
      :title="t('catalog.mappingTitle')"
      :subtitle="t('catalog.mappingSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      :loading="loading"
      :error="error"
      :batch-actions="batchActions"
      @retry="load"
      @batch="onBatch"
    >
      <template #item.platformSku="{ item }">
        <span class="font-weight-medium">{{ item.platformSku }}</span>
      </template>
      <template #item.internalSku="{ item }">
        <span>{{ item.internalSku }}</span>
      </template>
      <template #item.status="{ item }">
        <StatusChip
          domain="mapping"
          :value="item.status"
        />
      </template>
    </ListPage>
    <FormDrawer
      v-model="open"
      :title="t('catalog.createMapping')"
      :saving="saving"
      @save="save"
    >
      <AppSelect
        v-model="form.storeId"
        :items="stores.map(item => ({ title: item.label, value: item.id }))"
        :label="t('common.store')"
        :rules="[requiredText(t('common.store'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.platformSku"
        :label="t('catalog.platformSku')"
        :rules="[requiredText(t('catalog.platformSku'))]"
        class="mb-4"
      />
      <AppAutocomplete
        v-model="form.internalSku"
        :items="skus.map(item => item.label.split(' ')[0])"
        :label="t('catalog.sku')"
        :rules="[requiredText(t('catalog.sku'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="form.status"
        :items="[{ title: t('catalog.suggest'), value: 'suggested' }, { title: t('catalog.confirm'), value: 'confirmed' }]"
        :label="t('common.status')"
      />
    </FormDrawer>
  </div>
</template>
