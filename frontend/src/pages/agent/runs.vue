<script setup lang="ts">
import { fetchAgentRuns } from '@/api/agent'
import type { AgentRun, AgentRunStatus } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<AgentRun[]>([])

onMounted(async () => {
  rows.value = await fetchAgentRuns()
})

const headers = computed(() => [
  { title: t('runs.agent'), key: 'agentName' },
  { title: t('runs.startedAt'), key: 'startedAt' },
  { title: t('runs.duration'), key: 'durationMs', align: 'end' as const },
  { title: t('runs.tokens'), key: 'tokens', align: 'end' as const },
  { title: t('runs.cost'), key: 'costUsd', align: 'end' as const },
  { title: t('common.status'), key: 'status' },
  { title: t('runs.question'), key: 'question' },
])

function statusLabel(status: AgentRunStatus) {
  return t(`runs.${status}`)
}

function statusColor(status: AgentRunStatus) {
  if (status === 'succeeded')
    return 'success'
  if (status === 'failed')
    return 'error'

  return 'info'
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        {{ t('runs.title') }}
      </h4>
      <p class="text-body-1 text-medium-emphasis mb-0">
        {{ t('runs.subtitle') }}
      </p>
    </div>
    <VCard>
      <VDataTable
        :headers="headers"
        :items="rows"
        :items-per-page="10"
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
            {{ statusLabel(item.status) }}
          </VChip>
        </template>
      </VDataTable>
    </VCard>
  </div>
</template>
