<script setup lang="ts">
import { changeSupplierStatus, createSupplier, fetchSupplier, fetchSuppliers, updateSupplier } from '@/api/procurement'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useConfirm } from '@/composables/useConfirm'
import { usePageContext } from '@/composables/usePageContext'
import { useSessionStore } from '@/stores/session'
import type { CurrencyCode, SupplierRow } from '@/types/domain'
import { requiredText } from '@core/utils/validators'
import { can } from '@/utils/permission'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const session = useSessionStore()
const { confirm } = useConfirm()
const { setSelected } = usePageContext()
const rows = ref<SupplierRow[]>([])
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const editingId = ref('')

const form = reactive({
  name: '',
  country: 'CN',
  currency: 'CNY' as CurrencyCode,
  remark: '',
  contactName: '',
  email: '',
  phone: '',
})

const currencies = ['USD', 'CNY', 'EUR', 'GBP', 'JPY'].map(item => ({ title: item, value: item }))

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchSuppliers()
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
  { key: 'name', title: t('procurement.supplier') },
  { key: 'country', title: t('inventory.country') },
  { key: 'currency', title: t('procurement.currency') },
  { key: 'status', title: t('common.status') },
  { key: 'contact', title: t('procurement.contact') },
  { key: 'openPo', title: t('procurement.openPo'), align: 'end' as const },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [
  {
    key: 'country',
    label: t('inventory.country'),
    items: [...new Set(rows.value.map(item => item.country))].map(name => ({ title: name, value: name })),
  },
  {
    key: 'status',
    label: t('common.status'),
    items: [
      { title: t('procurement.resume'), value: 'active' },
      { title: t('procurement.pause'), value: 'paused' },
    ],
  },
])

const batchActions = computed(() => can(session.role, 'update')
  ? [{ key: 'active', label: t('procurement.resume') }, { key: 'paused', label: t('procurement.pause') }]
  : [])

function startCreate() {
  editingId.value = ''
  form.name = ''
  form.country = 'CN'
  form.currency = 'CNY'
  form.remark = ''
  form.contactName = ''
  form.email = ''
  form.phone = ''
  open.value = true
}

async function startEdit(row: SupplierRow) {
  const detail = await fetchSupplier(row.id)
  const contact = detail?.contacts[0]

  editingId.value = row.id
  form.name = detail?.name ?? row.name
  form.country = detail?.country ?? row.country
  form.currency = detail?.currency ?? row.currency
  form.remark = detail?.remark ?? ''
  form.contactName = contact?.name ?? ''
  form.email = contact?.email ?? ''
  form.phone = contact?.phone ?? ''
  open.value = true
}

function openRow(row: SupplierRow) {
  setSelected(row.id)
  router.push({ path: `/procurement/suppliers/${row.id}` })
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    if (editingId.value)
      await updateSupplier(editingId.value, { ...form })
    else
      await createSupplier({ ...form })

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

async function onBatch(action: string, selected: SupplierRow[]) {
  if (action === 'paused') {
    const ok = await confirm({
      title: t('procurement.pause'),
      text: selected.map(item => item.name).join(', '),
      confirmText: t('procurement.pause'),
      cancelText: t('foundation.cancel'),
    })

    if (!ok)
      return
  }

  try {
    await changeSupplierStatus(selected.map(item => item.id), action === 'active' ? 'active' : 'paused')
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
          {{ t('procurement.createSupplier') }}
        </VBtn>
      </PermissionGate>
    </div>
    <ListPage
      storage-key="procurement-suppliers"
      :title="t('procurement.suppliersTitle')"
      :subtitle="t('procurement.suppliersSubtitle')"
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
          domain="supplier"
          :value="item.status"
        />
      </template>
      <template #item.actions="{ item }">
        <VBtn
          size="small"
          variant="text"
          :to="{ path: `/procurement/suppliers/${item.id}` }"
        >
          {{ t('common.view') }}
        </VBtn>
        <PermissionGate action="update">
          <VBtn
            size="small"
            variant="text"
            @click="startEdit(item)"
          >
            {{ t('procurement.editSupplier') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
    <FormDrawer
      v-model="open"
      :title="editingId ? t('procurement.editSupplier') : t('procurement.createSupplier')"
      :saving="saving"
      @save="save"
    >
      <AppTextField
        v-model="form.name"
        :label="t('procurement.supplier')"
        :rules="[requiredText(t('procurement.supplier'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.country"
        :label="t('inventory.country')"
        class="mb-4"
      />
      <AppSelect
        v-model="form.currency"
        :items="currencies"
        :label="t('procurement.currency')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.contactName"
        :label="t('procurement.contact')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.email"
        :label="t('procurement.email')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.phone"
        :label="t('procurement.phone')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.remark"
        :label="t('procurement.remark')"
      />
    </FormDrawer>
  </div>
</template>
