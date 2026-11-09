<script setup lang="ts">
import { fetchReconRuns } from '@/api/finance'
import ListPage from '@/components/biz/ListPage.vue'
import type { ReconRun } from '@/types/domain'
import { formatInteger, formatPercent } from '@/utils/format'

const { t } = useI18n({ useScope: 'global' })
const runs = ref<ReconRun[]>([])

onMounted(async () => {
  runs.value = await fetchReconRuns()
})

const columns = computed(() => [
  { key: 'storeName', title: t('common.store') },
  { key: 'period', title: t('common.period') },
  { key: 'matched', title: t('recon.matched'), align: 'end' as const },
  { key: 'unmatched', title: t('recon.unmatched'), align: 'end' as const },
  { key: 'matchRate', title: t('recon.matchRate'), align: 'end' as const },
  { key: 'status', title: t('common.status') },
  { key: 'finishedAt', title: t('recon.finishedAt') },
])

const filters = computed(() => [{
  key: 'storeName',
  label: t('common.store'),
  store: true,
  items: [...new Set(runs.value.map(item => item.storeName))].map(name => ({ title: name, value: name })),
}])
</script>

<template>
  <div>
    <ListPage
      storage-key="finance-recon"
      :title="t('recon.title')"
      :subtitle="t('recon.subtitle')"
      :items="runs"
      :columns="columns"
      :filters="filters"
    >
      <template #widgets>
        <div class="d-flex justify-end mb-4">
          <VBtn
            to="/finance/issues"
            prepend-icon="tabler-alert-circle"
          >
            {{ t('recon.openIssues') }}
          </VBtn>
        </div>
        <VRow class="mb-6">
          <VCol
            v-for="run in runs.slice(0, 4)"
            :key="run.id"
            cols="12"
            sm="6"
            lg="3"
          >
            <KpiCard
              :title="`${run.storeName} ${run.period}`"
              :value="formatPercent(run.matchRate)"
              :hint="`${formatInteger(run.matched)} / ${formatInteger(run.unmatched)}`"
              icon="tabler-arrows-join"
              color="info"
            />
          </VCol>
        </VRow>
      </template>
      <template #item.matched="{ item }">
        {{ formatInteger(item.matched) }}
      </template>
      <template #item.unmatched="{ item }">
        {{ formatInteger(item.unmatched) }}
      </template>
      <template #item.matchRate="{ item }">
        {{ formatPercent(item.matchRate) }}
      </template>
    </ListPage>
  </div>
</template>
