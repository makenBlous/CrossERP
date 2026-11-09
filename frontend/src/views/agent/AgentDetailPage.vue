<script setup lang="ts">
import { fetchAgentDefinitions, fetchAgentRuns } from '@/api/agent'
import { fetchAgentTask, fetchEvalCases, fetchEvalRuns, fetchKnowledgeDocuments, fetchRunSteps, fetchUsageCalls } from '@/api/agent-module'
import DetailPage from '@/components/biz/DetailPage.vue'
import type { AgentDefinition, AgentRun } from '@/types/domain'
import type { AgentRunStep, AgentTask, EvalCase, EvalRun, KnowledgeDocument, UsageCall } from '@/types/agent-module'

type DetailMode = 'definition' | 'task' | 'run' | 'knowledge' | 'eval' | 'usage'
const props = defineProps<{ mode: DetailMode }>()
const route = useRoute()
const { t } = useI18n({ useScope: 'global' })
const routeParams = route.params as Record<string, unknown>
const id = computed(() => typeof routeParams.id === 'string' ? routeParams.id : '')
const definition = ref<AgentDefinition | null>(null)
const task = ref<AgentTask | null>(null)
const run = ref<AgentRun | null>(null)
const steps = ref<AgentRunStep[]>([])
const docs = ref<KnowledgeDocument[]>([])
const evalRun = ref<EvalRun | null>(null)
const evalCases = ref<EvalCase[]>([])
const call = ref<UsageCall | null>(null)
const activeTab = ref('basics')
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    if (props.mode === 'definition')
      definition.value = (await fetchAgentDefinitions()).find(item => item.id === id.value) ?? null
    if (props.mode === 'task')
      task.value = await fetchAgentTask(id.value)
    if (props.mode === 'run') {
      run.value = (await fetchAgentRuns()).find(item => item.id === id.value) ?? null
      steps.value = await fetchRunSteps(id.value)
    }
    if (props.mode === 'knowledge')
      docs.value = await fetchKnowledgeDocuments(id.value)
    if (props.mode === 'eval') {
      evalRun.value = (await fetchEvalRuns()).find(item => item.id === id.value) ?? null
      evalCases.value = await fetchEvalCases(id.value)
    }
    if (props.mode === 'usage')
      call.value = (await fetchUsageCalls()).find(item => item.id === id.value) ?? null
  }
  finally { loading.value = false }
}
onMounted(load)

const money = (value: number) => `$${value.toFixed(3)}`
const timeline = computed(() => steps.value.map(step => ({ id: step.id, at: step.at, title: step.title, detail: step.detail })))
const taskTimeline = computed(() => task.value?.steps.map((step, index) => ({ id: `${index}`, at: task.value?.nextRun ?? '', title: step, detail: t('agentModule.stepReady') })) ?? [])
</script>

<template>
  <VSkeletonLoader
    v-if="loading"
    type="card, table"
  />
  <DetailPage
    v-else-if="props.mode === 'definition' && definition"
    :title="definition.name"
    :subtitle="definition.duty"
    :timeline="[]"
    :related="[]"
  >
    <VCard>
      <VTabs
        v-model="activeTab"
        class="px-4"
      >
        <VTab value="basics">
          {{ t('agentModule.tabs.basics') }}
        </VTab><VTab value="model">
          {{ t('agentModule.tabs.model') }}
        </VTab><VTab value="tools">
          {{ t('agentModule.tabs.tools') }}
        </VTab><VTab value="prompt">
          {{ t('agentModule.tabs.prompt') }}
        </VTab>
      </VTabs><VDivider /><VWindow v-model="activeTab">
        <VWindowItem value="basics">
          <VCardText>
            <VChip color="success">
              {{ definition.status }}
            </VChip><p class="mt-4">
              {{ t('agentModule.scope') }}：{{ definition.storeScope }}
            </p>
          </VCardText>
        </VWindowItem><VWindowItem value="model">
          <VCardText>
            <AppTextField
              :model-value="definition.model"
              label="Model"
              readonly
            />
          </VCardText>
        </VWindowItem><VWindowItem value="tools">
          <VCardText>
            <VChip
              v-for="tool in definition.tools"
              :key="tool"
              class="me-2 mb-2"
              variant="tonal"
            >
              {{ tool }}
            </VChip>
          </VCardText>
        </VWindowItem><VWindowItem value="prompt">
          <VCardText>
            <VTextarea
              model-value="你是 CrossERP 只读助手。写操作只能生成待审批建议。"
              readonly
              rows="5"
            />
          </VCardText>
        </VWindowItem>
      </VWindow>
    </VCard>
  </DetailPage>
  <DetailPage
    v-else-if="props.mode === 'task' && task"
    :title="task.name"
    :subtitle="task.schedule"
    :timeline="taskTimeline"
    :related="[]"
  >
    <VCardText><VChip>{{ task.status }}</VChip></VCardText>
  </DetailPage>
  <DetailPage
    v-else-if="props.mode === 'run' && run"
    :title="run.id"
    :subtitle="`${run.agentName} · ${run.tokens.toLocaleString()} tokens · ${money(run.costUsd)}`"
    :timeline="timeline"
    :related="[]"
  >
    <VCardText>{{ run.question }}</VCardText>
  </DetailPage>
  <DetailPage
    v-else-if="props.mode === 'knowledge'"
    :title="t('agentModule.knowledge.detailTitle')"
    :subtitle="t('agentModule.knowledge.chunksHint')"
    :timeline="[]"
    :related="[]"
  >
    <VExpansionPanels>
      <VExpansionPanel
        v-for="doc in docs"
        :key="doc.id"
        :title="doc.name"
      >
        <VExpansionPanelText>{{ doc.chunks }} chunks · {{ doc.status }}</VExpansionPanelText>
      </VExpansionPanel>
    </VExpansionPanels>
  </DetailPage>
  <DetailPage
    v-else-if="props.mode === 'eval' && evalRun"
    :title="evalRun.name"
    :subtitle="`${evalRun.model} · ${Math.round(evalRun.passRate)}%`"
    :timeline="[]"
    :related="[]"
  >
    <VList>
      <VListItem
        v-for="item in evalCases"
        :key="item.id"
        :title="item.question"
        :subtitle="item.actual"
      >
        <template #append>
          <VChip
            size="small"
            :color="item.passed ? 'success' : 'error'"
          >
            {{ item.passed ? '通过' : '未通过' }}
          </VChip>
        </template>
      </VListItem>
    </VList>
  </DetailPage>
  <DetailPage
    v-else-if="props.mode === 'usage' && call"
    :title="call.id"
    :subtitle="`${call.model} · ${call.createdAt}`"
    :timeline="[]"
    :related="[]"
  >
    <VRow>
      <VCol
        cols="6"
        md="3"
      >
        <div class="text-caption">
          Input
        </div><div class="text-h6">
          {{ call.inputTokens }}
        </div>
      </VCol><VCol
        cols="6"
        md="3"
      >
        <div class="text-caption">
          Output
        </div><div class="text-h6">
          {{ call.outputTokens }}
        </div>
      </VCol><VCol
        cols="6"
        md="3"
      >
        <div class="text-caption">
          Total
        </div><div class="text-h6">
          {{ call.totalTokens }}
        </div>
      </VCol><VCol
        cols="6"
        md="3"
      >
        <div class="text-caption">
          Cost
        </div><div class="text-h6">
          {{ money(call.costUsd) }}
        </div>
      </VCol>
    </VRow><VDivider class="my-4" /><VChip
      v-for="flag in call.redactionFlags"
      :key="flag"
      class="me-2"
      variant="tonal"
    >
      redacted: {{ flag }}
    </VChip>
  </DetailPage>
  <EmptyState
    v-else
    :text="t('foundation.noData')"
  />
</template>
