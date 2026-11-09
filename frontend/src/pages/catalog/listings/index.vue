<script setup lang="ts">
import { changeListingStatus, createListing, fetchCatalogLookups, fetchListings } from '@/api/catalog'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { usePageContext } from '@/composables/usePageContext'
import { useSessionStore } from '@/stores/session'
import type { CurrencyCode, ListingListRow, LookupOption } from '@/types/domain'
import { moneyText, requiredText } from '@core/utils/validators'
import { can } from '@/utils/permission'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const session = useSessionStore()
const { setSelected } = usePageContext()
const rows = ref<ListingListRow[]>([])
const stores = ref<LookupOption[]>([])
const skus = ref<LookupOption[]>([])
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const currencies: CurrencyCode[] = ['USD', 'EUR', 'GBP', 'JPY', 'CNY']

const form = reactive({
  storeId: '',
  skuId: '',
  platformListingId: '',
  title: '',
  status: 'active',
  price: '',
  currency: 'USD' as CurrencyCode,
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [list, lookups] = await Promise.all([fetchListings(), fetchCatalogLookups()])

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
  { key: 'platform', title: t('orders.platform') },
  { key: 'marketplace', title: t('common.store') },
  { key: 'storeName', title: t('common.store') },
  { key: 'title', title: t('catalog.name') },
  { key: 'platformListingId', title: t('catalog.listingId') },
  { key: 'internalSku', title: t('catalog.sku') },
  { key: 'status', title: t('common.status') },
  { key: 'price', title: t('catalog.price'), align: 'end' as const },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [
  { key: 'platform', label: t('orders.platform'), items: [...new Set(rows.value.map(item => item.platform))].map(name => ({ title: name, value: name })) },
  { key: 'marketplace', label: t('common.store'), items: [...new Set(rows.value.map(item => item.marketplace))].map(name => ({ title: name, value: name })) },
  { key: 'status', label: t('common.status'), items: [...new Set(rows.value.map(item => item.status))].map(name => ({ title: name, value: name })) },
])

const batchActions = computed(() => can(session.role, 'update')
  ? [{ key: 'pause', label: t('catalog.pause') }, { key: 'active', label: t('catalog.enable') }]
  : [])

function startCreate() {
  Object.assign(form, {
    storeId: stores.value[0]?.id ?? '',
    skuId: skus.value[0]?.id ?? '',
    platformListingId: '',
    title: '',
    status: 'active',
    price: '',
    currency: 'USD' as CurrencyCode,
  })
  open.value = true
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    await createListing({ ...form })
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

async function onBatch(action: string, selected: ListingListRow[]) {
  try {
    await changeListingStatus(selected.map(item => item.id), action)
    await load()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}

function openRow(row: ListingListRow) {
  setSelected(row.id)
  router.push({ path: `/catalog/listings/${row.id}` })
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
          {{ t('catalog.createListing') }}
        </VBtn>
      </PermissionGate>
    </div>
    <ListPage
      storage-key="catalog-listings"
      :title="t('catalog.listingTitle')"
      :subtitle="t('catalog.listingSubtitle')"
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
      <template #item.price="{ item }">
        <MoneyText
          :amount="item.price"
          :currency="item.currency"
        />
      </template>
      <template #item.actions="{ item }">
        <VBtn
          size="small"
          variant="text"
          :to="{ path: `/catalog/listings/${item.id}` }"
        >
          {{ t('common.view') }}
        </VBtn>
      </template>
    </ListPage>
    <FormDrawer
      v-model="open"
      :title="t('catalog.createListing')"
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
      <AppSelect
        v-model="form.skuId"
        :items="skus.map(item => ({ title: item.label, value: item.id }))"
        :label="t('catalog.mappedSku')"
        :rules="[requiredText(t('catalog.sku'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.platformListingId"
        :label="t('catalog.listingId')"
        :rules="[requiredText(t('catalog.listingId'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.title"
        :label="t('catalog.name')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.price"
        :label="t('catalog.price')"
        :rules="[requiredText(t('catalog.price')), moneyText(t('catalog.price'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="form.currency"
        :items="currencies"
        :label="t('common.amount')"
      />
    </FormDrawer>
  </div>
</template>
