<script setup lang="ts">
import { createRateCard, fetchRateCards, updateRateCard } from '@/api/logistics'
import { fetchSupplyLookups } from '@/api/procurement'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import type { CurrencyCode, RateCardRow, SupplyLookups } from '@/types/domain'
import { moneyText, requiredText } from '@core/utils/validators'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<RateCardRow[]>([])
const lookups = ref<SupplyLookups | null>(null)
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const editingId = ref('')

const form = reactive({
  carrierId: '',
  dest: 'US',
  unit: 'kg',
  price: '6.8000',
  currency: 'CNY' as CurrencyCode,
  validFrom: '2026-01-01',
})

const currencies = ['USD', 'CNY', 'EUR', 'GBP', 'JPY'].map(item => ({ title: item, value: item }))

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchRateCards()
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
  { key: 'carrierName', title: t('logistics.carrier') },
  { key: 'dest', title: t('logistics.dest') },
  { key: 'unit', title: t('logistics.unit') },
  { key: 'price', title: t('logistics.price'), align: 'end' as const },
  { key: 'validFrom', title: t('logistics.validFrom') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [{
  key: 'dest',
  label: t('logistics.dest'),
  items: [...new Set(rows.value.map(item => item.dest))].map(name => ({ title: name, value: name })),
}])

function startCreate() {
  editingId.value = ''
  form.carrierId = lookups.value?.carriers[0]?.id ?? ''
  form.dest = 'US'
  form.unit = 'kg'
  form.price = '6.8000'
  form.currency = 'CNY'
  form.validFrom = '2026-01-01'
  open.value = true
}

function startEdit(row: RateCardRow) {
  editingId.value = row.id
  form.carrierId = row.carrierId
  form.dest = row.dest
  form.unit = row.unit
  form.price = String(row.price)
  form.currency = row.currency
  form.validFrom = row.validFrom
  open.value = true
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    if (editingId.value)
      await updateRateCard(editingId.value, { ...form })
    else
      await createRateCard({ ...form })

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
          {{ t('logistics.createRate') }}
        </VBtn>
      </PermissionGate>
    </div>
    <ListPage
      storage-key="logistics-rate-cards"
      :title="t('logistics.ratesTitle')"
      :subtitle="t('logistics.ratesSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      date-key="validFrom"
      :loading="loading"
      :error="error"
      @retry="load"
    >
      <template #item.price="{ item }">
        <MoneyText
          :amount="item.price"
          :currency="item.currency"
        />
      </template>
      <template #item.actions="{ item }">
        <PermissionGate action="update">
          <VBtn
            size="small"
            variant="text"
            @click="startEdit(item)"
          >
            {{ t('logistics.editRate') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
    <FormDrawer
      v-model="open"
      :title="editingId ? t('logistics.editRate') : t('logistics.createRate')"
      :saving="saving"
      @save="save"
    >
      <AppSelect
        v-model="form.carrierId"
        :items="(lookups?.carriers ?? []).map(item => ({ title: item.label, value: item.id }))"
        :label="t('logistics.carrier')"
        :rules="[requiredText(t('logistics.carrier'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.dest"
        :label="t('logistics.dest')"
        :rules="[requiredText(t('logistics.dest'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.unit"
        :label="t('logistics.unit')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.price"
        :label="t('logistics.price')"
        :rules="[requiredText(t('logistics.price')), moneyText(t('logistics.price'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="form.currency"
        :items="currencies"
        :label="t('procurement.currency')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.validFrom"
        type="date"
        :label="t('logistics.validFrom')"
        :rules="[requiredText(t('logistics.validFrom'))]"
      />
    </FormDrawer>
  </div>
</template>
