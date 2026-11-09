<script setup lang="ts">
import { changeSkuActive, createSku, fetchCatalogLookups, fetchSkus, updateSku } from '@/api/catalog'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useConfirm } from '@/composables/useConfirm'
import { usePageContext } from '@/composables/usePageContext'
import { useSessionStore } from '@/stores/session'
import type { LookupOption, SkuListRow } from '@/types/domain'
import { requiredText } from '@/utils/form-rules'
import { can } from '@/utils/permission'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const session = useSessionStore()
const { confirm } = useConfirm()
const { setSelected } = usePageContext()
const rows = ref<SkuListRow[]>([])
const brands = ref<LookupOption[]>([])
const categories = ref<LookupOption[]>([])
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const editingId = ref('')
const form = reactive({ internalSku: '', title: '', titleEn: '', brandId: '', categoryId: '' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [list, lookups] = await Promise.all([fetchSkus(), fetchCatalogLookups()])

    rows.value = list
    brands.value = lookups.brands
    categories.value = lookups.categories
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
  { key: 'internalSku', title: t('catalog.sku') },
  { key: 'title', title: t('catalog.name') },
  { key: 'brandName', title: t('catalog.brand') },
  { key: 'categoryName', title: t('catalog.category') },
  { key: 'status', title: t('common.status') },
  { key: 'listingCount', title: t('catalog.listings') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [
  { key: 'brandName', label: t('catalog.brand'), items: [...new Set(rows.value.map(item => item.brandName))].map(name => ({ title: name, value: name })) },
  { key: 'categoryName', label: t('catalog.category'), items: [...new Set(rows.value.map(item => item.categoryName))].map(name => ({ title: name, value: name })) },
  { key: 'status', label: t('common.status'), items: [{ title: t('catalog.enable'), value: 'active' }, { title: t('catalog.disable'), value: 'disabled' }] },
])

const batchActions = computed(() => {
  if (!can(session.role, 'update'))
    return []

  return [
    { key: 'enable', label: t('catalog.enable') },
    { key: 'disable', label: t('catalog.disable') },
  ]
})

function startCreate() {
  editingId.value = ''
  Object.assign(form, { internalSku: '', title: '', titleEn: '', brandId: brands.value[0]?.id ?? '', categoryId: categories.value[0]?.id ?? '' })
  open.value = true
}

function startEdit(row: SkuListRow) {
  editingId.value = row.id
  Object.assign(form, {
    internalSku: row.internalSku,
    title: row.title,
    titleEn: '',
    brandId: brands.value.find(item => item.label === row.brandName)?.id ?? '',
    categoryId: categories.value.find(item => item.label === row.categoryName)?.id ?? '',
  })
  open.value = true
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    if (editingId.value)
      await updateSku(editingId.value, { ...form })
    else
      await createSku({ ...form })

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

async function onBatch(action: string, selected: SkuListRow[]) {
  if (!selected.length)
    return

  if (action === 'disable') {
    const ok = await confirm({
      title: t('catalog.disable'),
      text: selected.map(item => item.internalSku).join(', '),
      confirmText: t('catalog.disable'),
      cancelText: t('foundation.cancel'),
    })

    if (!ok)
      return
  }

  try {
    await changeSkuActive(selected.map(item => item.id), action === 'enable')
    await load()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}

function openRow(row: SkuListRow) {
  setSelected(row.id)
  router.push({ path: `/catalog/skus/${row.id}` })
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
          {{ t('catalog.createSku') }}
        </VBtn>
      </PermissionGate>
    </div>
    <ListPage
      storage-key="catalog-skus"
      :title="t('catalog.skuTitle')"
      :subtitle="t('catalog.skuSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      :loading="loading"
      :error="error"
      :batch-actions="batchActions"
      @retry="load"
      @open="openRow"
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
            {{ t('catalog.editSku') }}
          </VBtn>
        </PermissionGate>
        <VBtn
          size="small"
          variant="text"
          :to="{ path: `/catalog/skus/${item.id}` }"
        >
          {{ t('common.view') }}
        </VBtn>
      </template>
    </ListPage>
    <FormDrawer
      v-model="open"
      :title="editingId ? t('catalog.editSku') : t('catalog.createSku')"
      :saving="saving"
      @save="save"
    >
      <AppTextField
        v-model="form.internalSku"
        :label="t('catalog.sku')"
        :rules="[requiredText(t('catalog.sku'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.title"
        :label="t('catalog.name')"
        :rules="[requiredText(t('catalog.name'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.titleEn"
        :label="t('catalog.nameEn')"
        class="mb-4"
      />
      <AppSelect
        v-model="form.brandId"
        :items="brands.map(item => ({ title: item.label, value: item.id }))"
        :label="t('catalog.brand')"
        :rules="[requiredText(t('catalog.brand'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="form.categoryId"
        :items="categories.map(item => ({ title: item.label, value: item.id }))"
        :label="t('catalog.category')"
        :rules="[requiredText(t('catalog.category'))]"
      />
    </FormDrawer>
  </div>
</template>
