<script setup lang="ts">
import { changeCategoryActive, createCategory, fetchCategories, updateCategory } from '@/api/catalog'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useSessionStore } from '@/stores/session'
import type { CategoryRow } from '@/types/domain'
import { requiredText } from '@/utils/form-rules'
import { can } from '@/utils/permission'

const { t } = useI18n({ useScope: 'global' })
const session = useSessionStore()
const { confirm } = useConfirm()
const rows = ref<CategoryRow[]>([])
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const editingId = ref('')
const form = reactive({ name: '', parentId: '', sortNo: '1' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchCategories()
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
  { key: 'name', title: t('catalog.name') },
  { key: 'parentName', title: t('catalog.parent') },
  { key: 'sortNo', title: t('catalog.sortNo') },
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
  Object.assign(form, { name: '', parentId: '', sortNo: String(rows.value.length + 1) })
  open.value = true
}

function startEdit(row: CategoryRow) {
  editingId.value = row.id
  Object.assign(form, { name: row.name, parentId: row.parentId, sortNo: String(row.sortNo) })
  open.value = true
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    const input = { name: form.name, parentId: form.parentId || null, sortNo: Number(form.sortNo) }

    if (editingId.value)
      await updateCategory(editingId.value, input)
    else
      await createCategory(input)

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

async function onBatch(action: string, selected: CategoryRow[]) {
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
    await changeCategoryActive(selected.map(item => item.id), action === 'enable')
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
          {{ t('catalog.createCategory') }}
        </VBtn>
      </PermissionGate>
    </div>
    <ListPage
      storage-key="catalog-categories"
      :title="t('catalog.categoryTitle')"
      :subtitle="t('catalog.categorySubtitle')"
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
            {{ t('catalog.editCategory') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
    <FormDrawer
      v-model="open"
      :title="editingId ? t('catalog.editCategory') : t('catalog.createCategory')"
      :saving="saving"
      @save="save"
    >
      <AppTextField
        v-model="form.name"
        :label="t('catalog.name')"
        :rules="[requiredText(t('catalog.name'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="form.parentId"
        :items="[{ title: '—', value: '' }, ...rows.filter(item => item.id !== editingId).map(item => ({ title: item.name, value: item.id }))]"
        :label="t('catalog.parent')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.sortNo"
        :label="t('catalog.sortNo')"
        :rules="[requiredText(t('catalog.sortNo'))]"
      />
    </FormDrawer>
  </div>
</template>
