<script setup lang="ts">
import { fetchReconRuns } from '@/api/finance'
import type { ReconRun } from '@/types/domain'
import { formatInteger, formatPercent } from '@/utils/format'

const { t } = useI18n({ useScope: 'global' })
const runs = ref<ReconRun[]>([])

onMounted(async () => {
  runs.value = await fetchReconRuns()
})

const headers = computed(() => [
  { title: t('common.store'), key: 'storeName' },
  { title: t('common.period'), key: 'period' },
  { title: t('recon.matched'), key: 'matched', align: 'end' as const },
  { title: t('recon.unmatched'), key: 'unmatched', align: 'end' as const },
  { title: t('recon.matchRate'), key: 'matchRate', align: 'end' as const },
  { title: t('common.status'), key: 'status' },
  { title: t('recon.finishedAt'), key: 'finishedAt' },
])
</script>

<template>
  <div>
    <div class="d-flex flex-wrap justify-space-between align-center gap-4 mb-6">
      <div>
        <h4 class="text-h4">
          {{ t('recon.title') }}
        </h4>
        <p class="text-body-1 text-medium-emphasis mb-0">
          {{ t('recon.subtitle') }}
        </p>
      </div>
      <VBtn
        to="/finance/issues"
        prepend-icon="tabler-alert-circle"
      >
        {{ t('recon.openIssues') }}
      </VBtn>
    </div>
    <VRow class="mb-2">
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
    <VCard>
      <VDataTable
        :headers="headers"
        :items="runs"
        :items-per-page="10"
      >
        <template #item.matched="{ item }">
          {{ formatInteger(item.matched) }}
        </template>
        <template #item.unmatched="{ item }">
          {{ formatInteger(item.unmatched) }}
        </template>
        <template #item.matchRate="{ item }">
          {{ formatPercent(item.matchRate) }}
        </template>
      </VDataTable>
    </VCard>
  </div>
</template>
