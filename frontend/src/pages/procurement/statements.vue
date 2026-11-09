<script setup lang="ts">
import { fetchStatements, fetchSupplyLookups, generateStatement, submitStatement } from '@/api/procurement'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import type { StatementRow, SupplyLookups } from '@/types/domain'
import { requiredText } from '@core/utils/validators'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<StatementRow[]>([])
const lookups = ref<SupplyLookups | null>(null)
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const form = reactive({ supplierId: '', period: '2026-10' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchStatements()
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
  { key: 'no', title: t('inventory.docNo') },
  { key: 'supplierName', title: t('procurement.supplier') },
  { key: 'period', title: t('procurement.period') },
  { key: 'status', title: t('common.status') },
  { key: 'amount', title: t('procurement.amount'), align: 'end' as const },
  { key: 'receivedAmount', title: t('procurement.receivedAmount'), align: 'end' as const },
  { key: 'paidAmount', title: t('procurement.paidAmount'), align: 'end' as const },
  { key: 'variance', title: t('procurement.variance'), align: 'end' as const },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [{
  key: 'status',
  label: t('common.status'),
  items: [...new Set(rows.value.map(item => item.status))].map(name => ({ title: name, value: name })),
}])

function startCreate() {
  form.supplierId = lookups.value?.suppliers[0]?.id ?? ''
  form.period = '2026-10'
  open.value = true
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    await generateStatement(form.supplierId, form.period)
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

async function submit(row: StatementRow) {
  message.value = ''
  try {
    await submitStatement(row.id)
    await load()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}
</script>

<template>
  <div>
    <VAlert
      v-if="message"
      type="warning"
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
          {{ t('procurement.generate') }}
        </VBtn>
      </PermissionGate>
    </div>
    <ListPage
      storage-key="procurement-statements"
      :title="t('procurement.statementsTitle')"
      :subtitle="t('procurement.statementsSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      :loading="loading"
      :error="error"
      @retry="load"
    >
      <template #item.status="{ item }">
        <StatusChip
          domain="statement"
          :value="item.status"
        />
      </template>
      <template #item.amount="{ item }">
        <MoneyText
          :amount="item.amount"
          :currency="item.currency"
        />
      </template>
      <template #item.receivedAmount="{ item }">
        <MoneyText
          :amount="item.receivedAmount"
          :currency="item.currency"
        />
      </template>
      <template #item.paidAmount="{ item }">
        <MoneyText
          :amount="item.paidAmount"
          :currency="item.currency"
        />
      </template>
      <template #item.variance="{ item }">
        <MoneyText
          :amount="item.variance"
          :currency="item.currency"
        />
      </template>
      <template #item.actions="{ item }">
        <PermissionGate action="suggest">
          <VBtn
            v-if="item.status === 'draft'"
            size="small"
            variant="text"
            @click="submit(item)"
          >
            {{ t('procurement.submitStatement') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
    <FormDrawer
      v-model="open"
      :title="t('procurement.generate')"
      :saving="saving"
      @save="save"
    >
      <AppSelect
        v-model="form.supplierId"
        :items="(lookups?.suppliers ?? []).map(item => ({ title: item.label, value: item.id }))"
        :label="t('procurement.supplier')"
        :rules="[requiredText(t('procurement.supplier'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.period"
        :label="t('procurement.period')"
        :rules="[requiredText(t('procurement.period'))]"
      />
    </FormDrawer>
  </div>
</template>
