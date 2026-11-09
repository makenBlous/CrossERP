<script setup lang="ts">
import { fetchAgentDefinitions } from '@/api/agent'
import type { AgentDefinition } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const agents = ref<AgentDefinition[]>([])

onMounted(async () => {
  agents.value = await fetchAgentDefinitions()
})
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        {{ t('agents.title') }}
      </h4>
      <p class="text-body-1 text-medium-emphasis mb-0">
        {{ t('agents.subtitle') }}
      </p>
    </div>
    <VRow>
      <VCol
        v-for="agent in agents"
        :key="agent.id"
        cols="12"
        md="6"
      >
        <VCard class="h-100">
          <VCardItem>
            <template #prepend>
              <VAvatar
                color="primary"
                variant="tonal"
                rounded
              >
                <VIcon icon="tabler-robot" />
              </VAvatar>
            </template>
            <VCardTitle>{{ agent.name }}</VCardTitle>
            <VCardSubtitle>{{ agent.id }}</VCardSubtitle>
            <template #append>
              <VChip
                size="small"
                :color="agent.status === 'active' ? 'success' : 'warning'"
              >
                {{ agent.status === 'active' ? t('agents.active') : t('agents.paused') }}
              </VChip>
            </template>
          </VCardItem>
          <VCardText>
            <p>{{ agent.duty }}</p>
            <div class="text-body-2 mb-1">
              {{ t('agents.model') }}：{{ agent.model }}
            </div>
            <div class="text-body-2 mb-1">
              {{ t('agents.source') }}：{{ agent.source }}
            </div>
            <div class="text-body-2 mb-3">
              {{ t('agents.scope') }}：{{ agent.storeScope }}
            </div>
            <div class="text-caption text-medium-emphasis mb-2">
              {{ t('agents.tools') }}
            </div>
            <div class="d-flex flex-wrap gap-2">
              <VChip
                v-for="tool in agent.tools"
                :key="tool"
                size="small"
                variant="tonal"
              >
                {{ tool }}
              </VChip>
            </div>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>
