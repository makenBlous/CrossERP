<script setup lang="ts">
import { fetchAgentRuns } from '@/api/agent'
import ListPage from '@/components/biz/ListPage.vue'
import type { AgentRun } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<AgentRun[]>([])

onMounted(async () => {
  rows.value = await fetchAgentRuns()
})

const columns = computed(() => [
  { key: 'agentName', title: t('runs.agent') },
  { key: 'startedAt', title: t('runs.startedAt') },
  { key: 'durationMs', title: t('runs.duration'), align: 'end' as const },
  { key: 'tokens', title: t('runs.tokens'), align: 'end' as const },
  { key: 'costUsd', title: t('runs.cost'), align: 'end' as const },
  { key: 'status', title: t('common.status') },
  { key: 'question', title: t('runs.question') },
])

function statusColor(status: AgentRun['status']) {
  if (status === 'succeeded')
    return 'success'
  if (status === 'failed')
    return 'error'

  return 'info'
}

const filters = computed(() => [{
  key: 'status',
  label: t('common.status'),
  items: [
    { title: t('runs.succeeded'), value: 'succeeded' },
    { title: t('runs.failed'), value: 'failed' },
    { title: t('runs.running'), value: 'running' },
  ],
}])
</script>

<template>
  <ListPage
    storage-key="agent-runs"
    :title="t('runs.title')"
    :subtitle="t('runs.subtitle')"
    :items="rows"
    :columns="columns"
    :filters="filters"
  >
    <template #item.durationMs="{ item }">
      {{ (item.durationMs / 1000).toFixed(1) }} s
    </template>
    <template #item.tokens="{ item }">
      {{ item.tokens.toLocaleString('en-US') }}
    </template>
    <template #item.costUsd="{ item }">
      ${{ item.costUsd.toFixed(3) }}
    </template>
    <template #item.status="{ item }">
      <VChip
        size="small"
        :color="statusColor(item.status)"
      >
        {{ t(`runs.${item.status}`) }}
      </VChip>
    </template>
  </ListPage>
</template>
