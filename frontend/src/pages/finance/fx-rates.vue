<script setup lang="ts">
import { addFxRateEntry, fetchFxRates } from '@/api/finance'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchFxRates>>>([])
const open = ref(false)
const saving = ref(false)
const form = reactive({ period: '2026-11', fromCcy: 'EUR' as const, toCcy: 'USD' as const, rate: '1.08000000' })

onMounted(async () => {
  rows.value = await fetchFxRates()
})

const columns = [{ key: 'period', title: '期间' }, { key: 'fromCcy', title: '源币种' }, { key: 'toCcy', title: '目标币种' }, { key: 'rate', title: '汇率' }, { key: 'source', title: '来源' }]

async function save() {
  saving.value = true

  const row = await addFxRateEntry(form)

  saving.value = false
  if (row) {
    rows.value = [...rows.value, row]
    open.value = false
  }
}
</script>

<template>
  <div>
    <VAlert
      type="info"
      variant="tonal"
      class="mb-6"
    >
      汇率由用户提供，不调用实时汇率。
    </VAlert>
    <div class="d-flex justify-end mb-4">
      <VBtn
        prepend-icon="tabler-plus"
        @click="open = true"
      >
        新增月汇率
      </VBtn>
    </div>
    <FinanceTablePage
      storage-key="finance-fx"
      title="汇率表"
      subtitle="按期间与币种对维护用户提供的汇率。"
      :rows="rows as unknown as FinanceRow[]"
      :columns="columns"
    />
    <FormDrawer
      v-model="open"
      title="新增月汇率"
      :saving="saving"
      @save="save"
    >
      <AppTextField
        v-model="form.period"
        label="期间"
      />
      <AppSelect
        v-model="form.fromCcy"
        label="源币种"
        :items="['USD', 'CNY', 'EUR', 'GBP', 'JPY']"
      />
      <AppSelect
        v-model="form.toCcy"
        label="目标币种"
        :items="['USD', 'CNY', 'EUR', 'GBP', 'JPY']"
      />
      <AppTextField
        v-model="form.rate"
        label="汇率"
        type="number"
        :rules="[moneyText('最多 4 位小数')]"
      />
    </FormDrawer>
  </div>
</template>
