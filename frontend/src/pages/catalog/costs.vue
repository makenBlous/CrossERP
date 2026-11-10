<script setup lang="ts">
import { createCost, fetchCatalogLookups, fetchCosts } from '@/api/catalog'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import { usePageContext } from '@/composables/usePageContext'
import type { CostListRow, CurrencyCode, LookupOption } from '@/types/domain'
import { downloadCsv } from '@/utils/download-csv'
import { moneyText, requiredText } from '@core/utils/validators'

const { t } = useI18n({ useScope: 'global' })
const { setSelected } = usePageContext()
const rows = ref<CostListRow[]>([])
const skus = ref<LookupOption[]>([])
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const currencies: CurrencyCode[] = ['CNY', 'USD', 'EUR', 'GBP', 'JPY']

const form = reactive({
  internalSku: '',
  validFrom: '2026-11-01',
  unitCost: '',
  freightPerUnit: '',
  currency: 'CNY' as CurrencyCode,
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [list, lookups] = await Promise.all([fetchCosts(), fetchCatalogLookups()])

    rows.value = list
    skus.value = lookups.skus
    if (!form.internalSku)
      form.internalSku = lookups.skus[0]?.label.split(' ')[0] ?? ''
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
  { key: 'validFrom', title: t('catalog.validFrom') },
  { key: 'validTo', title: t('catalog.validTo') },
  { key: 'unitCost', title: t('catalog.unitCost'), align: 'end' as const },
  { key: 'freight', title: t('catalog.freight'), align: 'end' as const },
  { key: 'currency', title: t('common.amount') },
])

const filters = computed(() => [{
  key: 'currency',
  label: t('common.amount'),
  items: [...new Set(rows.value.map(item => item.currency))].map(name => ({ title: name, value: name })),
}])

async function save() {
  saving.value = true
  message.value = ''
  try {
    await createCost({ ...form })
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

async function importFile(file: File | File[] | null) {
  const picked = Array.isArray(file) ? file[0] : file

  if (!picked)
    return

  message.value = ''

  const text = await picked.text()
  const lines = text.split(/\r?\n/).map(line => line.trim()).filter(Boolean)

  for (const line of lines) {
    if (line.toLowerCase().startsWith('sku') || line.includes('货号'))
      continue

    const [internalSku, validFrom, unitCost, freightPerUnit, currency] = line.split(',').map(part => part.trim())

    if (!internalSku || !validFrom || !unitCost || !freightPerUnit || !currency)
      continue

    try {
      await createCost({
        internalSku,
        validFrom,
        unitCost,
        freightPerUnit,
        currency: currency as CurrencyCode,
      })
    }
    catch (err) {
      message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
    }
  }
  await load()
}

function exportSelected(selected: CostListRow[]) {
  downloadCsv('sku-costs.csv', ['sku', 'validFrom', 'unitCost', 'freight', 'currency'], selected.map(item => [
    item.internalSku,
    item.validFrom,
    String(item.unitCost),
    String(item.freight),
    item.currency,
  ]))
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
    <p class="text-body-2 text-medium-emphasis">
      {{ t('catalog.importHint') }}
    </p>
    <ListPage
      storage-key="catalog-costs"
      :title="t('catalog.costTitle')"
      :subtitle="t('catalog.costSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      date-key="validFrom"
      :loading="loading"
      :error="error"
      :batch-actions="[{ key: 'export', label: t('foundation.exportCsv') }]"
      @retry="load"
      @open="row => setSelected(row.id)"
      @batch="(_action, selected) => exportSelected(selected)"
    >
      <template #actions>
        <PermissionGate action="create">
          <VFileInput
            :label="t('catalog.importCost')"
            accept=".csv,text/csv"
            prepend-icon="tabler-upload"
            style="max-width: 280px;"
            hide-details
            @update:model-value="importFile"
          />
          <VBtn
            color="primary"
            @click="open = true"
          >
            {{ t('catalog.addCost') }}
          </VBtn>
        </PermissionGate>
      </template>
      <template #item.validTo="{ item }">
        {{ item.validTo || t('catalog.openEnded') }}
      </template>
      <template #item.unitCost="{ item }">
        <MoneyText
          :amount="item.unitCost"
          :currency="item.currency"
        />
      </template>
      <template #item.freight="{ item }">
        <MoneyText
          :amount="item.freight"
          :currency="item.currency"
        />
      </template>
    </ListPage>
    <FormDrawer
      v-model="open"
      :title="t('catalog.addCost')"
      :saving="saving"
      @save="save"
    >
      <AppSelect
        v-model="form.internalSku"
        :items="skus.map(item => ({ title: item.label, value: item.label.split(' ')[0] }))"
        :label="t('catalog.sku')"
        :rules="[requiredText(t('catalog.sku'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.validFrom"
        type="date"
        :label="t('catalog.validFrom')"
        :rules="[requiredText(t('catalog.validFrom'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.unitCost"
        :label="t('catalog.unitCost')"
        :rules="[requiredText(t('catalog.unitCost')), moneyText(t('catalog.unitCost'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.freightPerUnit"
        :label="t('catalog.freight')"
        :rules="[requiredText(t('catalog.freight')), moneyText(t('catalog.freight'))]"
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
