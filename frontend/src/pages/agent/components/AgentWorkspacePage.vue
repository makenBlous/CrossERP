<script setup lang="ts">
import { fetchAgentDefinitions, fetchAgentRuns, fetchChat } from '@/api/agent'
import { fetchAgentTask, fetchAgentTasks, fetchEvalCases, fetchEvalRuns, fetchKnowledgeDocuments, fetchPromptVersions, fetchRunSteps, fetchUsageCalls } from '@/api/agent-module'
import type { AgentDefinition, AgentRun, ChatThread } from '@/types/domain'
import type { AgentRunStep, AgentTask, EvalCase, EvalRun, KnowledgeDocument, PromptVersion, UsageCall } from '@/types/agent-module'

const props = defineProps<{ mode: string }>()
const { t } = useI18n({ useScope: 'global' })
const route = useRoute()
const router = useRouter()
const definitions = ref<AgentDefinition[]>([])
const runs = ref<AgentRun[]>([])
const threads = ref<ChatThread[]>([])
const tasks = ref<AgentTask[]>([])
const task = ref<AgentTask | null>(null)
const docs = ref<KnowledgeDocument[]>([])
const prompts = ref<PromptVersion[]>([])
const evalRuns = ref<EvalRun[]>([])
const evalCases = ref<EvalCase[]>([])
const steps = ref<AgentRunStep[]>([])
const usageCalls = ref<UsageCall[]>([])
const loading = ref(true)
const activeTab = ref('basics')
const selectedPrompt = ref<PromptVersion | null>(null)

const routeParams = route.params as Record<string, unknown>
const id = computed(() => typeof routeParams.id === 'string' ? routeParams.id : '')
const currentDefinition = computed(() => definitions.value.find(item => item.id === id.value) ?? definitions.value[0])
const currentRun = computed(() => runs.value.find(item => item.id === id.value) ?? runs.value[0])
const currentEval = computed(() => evalRuns.value.find(item => item.id === id.value) ?? evalRuns.value[0])
const currentCall = computed(() => usageCalls.value.find(item => item.id === id.value) ?? usageCalls.value[0])

const title = computed(() => {
  const map: Record<string, string> = { 'definitions': t('agentModule.definitions.title'), 'tools': t('agentModule.tools.title'), 'threads': t('agentModule.threads.title'), 'tasks': t('agentModule.tasks.title'), 'task-detail': t('agentModule.tasks.detail'), 'runs': t('agentModule.runs.title'), 'run-detail': t('agentModule.runs.detail'), 'knowledge': t('agentModule.knowledge.title'), 'knowledge-detail': t('agentModule.knowledge.detail'), 'prompts': t('agentModule.prompts.title'), 'evals': t('agentModule.evals.title'), 'eval-detail': t('agentModule.evals.detail'), 'usage': t('agentModule.usage.title'), 'usage-detail': t('agentModule.usage.detail'), 'deerflow': t('agentModule.deerflow.title') }

  return map[props.mode] ?? t('agentModule.title')
})

async function load() {
  loading.value = true
  try {
    if (['definitions', 'definition-detail', 'tools'].includes(props.mode))
      definitions.value = await fetchAgentDefinitions()
    if (['runs', 'run-detail'].includes(props.mode))
      runs.value = await fetchAgentRuns()
    if (props.mode === 'threads')
      threads.value = (await fetchChat()).threads
    if (props.mode === 'tasks')
      tasks.value = await fetchAgentTasks()
    if (props.mode === 'task-detail')
      task.value = await fetchAgentTask(id.value)
    if (['knowledge', 'knowledge-detail'].includes(props.mode))
      docs.value = await fetchKnowledgeDocuments()
    if (props.mode === 'prompts')
      prompts.value = await fetchPromptVersions()
    if (['evals', 'eval-detail'].includes(props.mode))
      evalRuns.value = await fetchEvalRuns()
    if (props.mode === 'eval-detail' && id.value)
      evalCases.value = await fetchEvalCases(id.value)
    if (props.mode === 'run-detail' && id.value)
      steps.value = await fetchRunSteps(id.value)
    if (['usage', 'usage-detail'].includes(props.mode))
      usageCalls.value = await fetchUsageCalls()
  }
  finally { loading.value = false }
}

onMounted(load)
watch(() => props.mode, load)
function money(value: number) {
  return `$${value.toFixed(3)}`
}
function go(path: string) {
  router.push(path).catch(() => undefined)
}
</script>

<template>
  <div>
    <div class="d-flex align-center justify-space-between mb-6 flex-wrap gap-3">
      <div>
        <h4 class="text-h4">
          {{ title }}
        </h4><p class="text-body-1 text-medium-emphasis mb-0">
          {{ t('agentModule.subtitle') }}
        </p>
      </div><VChip
        color="info"
        variant="tonal"
      >
        <VIcon
          start
          icon="tabler-shield-lock"
        />{{ t('agentModule.readOnly') }}
      </VChip>
    </div>
    <VAlert
      v-if="props.mode === 'tools' || props.mode === 'deerflow'"
      type="warning"
      variant="tonal"
      class="mb-6"
    >
      {{ t('agentModule.writeBoundary') }}
    </VAlert>
    <VSkeletonLoader
      v-if="loading"
      type="card, table"
    />

    <template v-else-if="props.mode === 'definitions'">
      <VRow>
        <VCol
          v-for="agent in definitions"
          :key="agent.id"
          cols="12"
          md="6"
          xl="4"
        >
          <VCard class="h-100">
            <VCardItem>
              <template #prepend>
                <VAvatar
                  color="primary"
                  variant="tonal"
                >
                  <VIcon icon="tabler-robot" />
                </VAvatar>
              </template><VCardTitle>{{ agent.name }}</VCardTitle><VCardSubtitle>{{ agent.id }}</VCardSubtitle><template #append>
                <VChip
                  size="small"
                  :color="agent.status === 'active' ? 'success' : 'warning'"
                >
                  {{ agent.status === 'active' ? t('agentModule.active') : t('agentModule.paused') }}
                </VChip>
              </template>
            </VCardItem><VCardText>
              <p class="mb-4">
                {{ agent.duty }}
              </p><div class="text-body-2">
                {{ t('agentModule.model') }}：<strong>{{ agent.model }}</strong>
              </div><div class="text-body-2 mb-3">
                {{ t('agentModule.scope') }}：{{ agent.storeScope }}
              </div><div class="d-flex flex-wrap gap-2">
                <VChip
                  v-for="tool in agent.tools"
                  :key="tool"
                  size="small"
                  variant="tonal"
                >
                  {{ tool }}
                </VChip>
              </div><VBtn
                class="mt-4"
                variant="text"
                append-icon="tabler-arrow-right"
                @click="go(`/agent/definitions/${agent.id}`)"
              >
                {{ t('common.view') }}
              </VBtn>
            </VCardText>
          </VCard>
        </VCol>
      </VRow>
    </template>

    <template v-else-if="props.mode === 'definition-detail' && currentDefinition">
      <VCard>
        <VCardItem>
          <template #prepend>
            <VAvatar
              color="primary"
              variant="tonal"
            >
              <VIcon icon="tabler-robot" />
            </VAvatar>
          </template><VCardTitle>{{ currentDefinition.name }}</VCardTitle><VCardSubtitle>{{ currentDefinition.duty }}</VCardSubtitle>
        </VCardItem><VTabs
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
          </VTab><VTab value="knowledge">
            {{ t('agentModule.tabs.knowledge') }}
          </VTab><VTab value="runs">
            {{ t('agentModule.tabs.runs') }}
          </VTab>
        </VTabs><VDivider /><VWindow v-model="activeTab">
          <VWindowItem value="basics">
            <VCardText>
              <VRow>
                <VCol
                  cols="12"
                  md="6"
                >
                  <div class="text-caption">
                    {{ t('agentModule.status') }}
                  </div><VChip
                    color="success"
                    size="small"
                  >
                    {{ t('agentModule.active') }}
                  </VChip>
                </VCol><VCol
                  cols="12"
                  md="6"
                >
                  <div class="text-caption">
                    {{ t('agentModule.scope') }}
                  </div><div>{{ currentDefinition.storeScope }}</div>
                </VCol>
              </VRow>
            </VCardText>
          </VWindowItem><VWindowItem value="model">
            <VCardText>
              <VTextField
                :model-value="currentDefinition.model"
                label="Model"
                readonly
              /><VAlert
                type="info"
                variant="tonal"
              >
                {{ t('agentModule.modelNote') }}
              </VAlert>
            </VCardText>
          </VWindowItem><VWindowItem value="tools">
            <VCardText>
              <VChip
                v-for="tool in currentDefinition.tools"
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
          </VWindowItem><VWindowItem value="knowledge">
            <VCardText>
              <VList>
                <VListItem
                  prepend-icon="tabler-book"
                  title="对账规则"
                  subtitle="已启用 · 32 个 chunks"
                />
              </VList>
            </VCardText>
          </VWindowItem><VWindowItem value="runs">
            <VCardText>
              <VBtn
                variant="tonal"
                @click="go('/agent/runs')"
              >
                {{ t('agentModule.openRuns') }}
              </VBtn>
            </VCardText>
          </VWindowItem>
        </VWindow>
      </VCard>
    </template>

    <template v-else-if="props.mode === 'tools'">
      <VCard>
        <VTable>
          <thead>
            <tr>
              <th>{{ t('agentModule.tool') }}</th><th>{{ t('agentModule.type') }}</th><th
                v-for="agent in definitions"
                :key="agent.id"
              >
                {{ agent.name }}
              </th>
            </tr>
          </thead><tbody>
            <tr
              v-for="tool in ['get_profit', 'list_issues', 'get_order', 'propose_issue_note']"
              :key="tool"
            >
              <td class="font-weight-medium">
                {{ tool }}
              </td><td>
                <VChip
                  size="small"
                  :color="tool === 'propose_issue_note' ? 'warning' : 'success'"
                >
                  {{ tool === 'propose_issue_note' ? t('agentModule.suggestionOnly') : t('agentModule.readOnly') }}
                </VChip>
              </td><td
                v-for="agent in definitions"
                :key="agent.id"
              >
                <VIcon
                  :color="agent.tools.includes(tool) ? 'success' : 'disabled'"
                  :icon="agent.tools.includes(tool) ? 'tabler-check' : 'tabler-minus'"
                />
              </td>
            </tr>
          </tbody>
        </VTable>
      </VCard>
    </template>
    <template v-else-if="props.mode === 'threads'">
      <VCard>
        <VList lines="two">
          <VListItem
            v-for="thread in threads"
            :key="thread.id"
            prepend-icon="tabler-message"
            :title="thread.title"
            :subtitle="thread.updatedAt"
            append-icon="tabler-chevron-right"
            @click="go('/agent/chat')"
          />
        </VList>
      </VCard>
    </template>
    <template v-else-if="props.mode === 'tasks'">
      <VRow>
        <VCol
          v-for="item in tasks"
          :key="item.id"
          cols="12"
          md="4"
        >
          <VCard class="h-100">
            <VCardItem>
              <VCardTitle>{{ item.name }}</VCardTitle><template #append>
                <VChip
                  size="small"
                  :color="item.status === 'active' ? 'success' : 'warning'"
                >
                  {{ item.status === 'active' ? t('agentModule.active') : t('agentModule.paused') }}
                </VChip>
              </template>
            </VCardItem><VCardText>
              <div class="text-body-2 mb-2">
                {{ item.schedule }}
              </div><div class="text-caption">
                {{ t('agentModule.nextRun') }}：{{ item.nextRun }}
              </div><VList
                density="compact"
                class="mt-3"
              >
                <VListItem
                  v-for="step in item.steps"
                  :key="step"
                  prepend-icon="tabler-point"
                >
                  {{ step }}
                </VListItem>
              </VList><VBtn
                variant="text"
                @click="go(`/agent/tasks/${item.id}`)"
              >
                {{ t('common.view') }}
              </VBtn>
            </VCardText>
          </VCard>
        </VCol>
      </VRow>
    </template>
    <template v-else-if="props.mode === 'task-detail' && task">
      <VCard>
        <VCardItem><VCardTitle>{{ task.name }}</VCardTitle><VCardSubtitle>{{ task.schedule }} · {{ task.status }}</VCardSubtitle></VCardItem><VCardText>
          <VTimeline
            density="compact"
            side="end"
          >
            <VTimelineItem
              v-for="(step, index) in task.steps"
              :key="step"
              dot-color="primary"
            >
              <div class="font-weight-medium">
                {{ index + 1 }}. {{ step }}
              </div><div class="text-caption text-medium-emphasis">
                {{ t('agentModule.stepReady') }}
              </div>
            </VTimelineItem>
          </VTimeline><VDivider class="my-4" /><VBtn
            variant="tonal"
            @click="go('/agent/runs')"
          >
            {{ t('agentModule.openRuns') }}
          </VBtn>
        </VCardText>
      </VCard>
    </template>
    <template v-else-if="props.mode === 'runs'">
      <VCard>
        <VTable>
          <thead><tr><th>{{ t('agentModule.run') }}</th><th>{{ t('agentModule.agent') }}</th><th>{{ t('agentModule.question') }}</th><th>{{ t('agentModule.tokens') }}</th><th>{{ t('agentModule.cost') }}</th><th>{{ t('common.status') }}</th></tr></thead><tbody>
            <tr
              v-for="run in runs"
              :key="run.id"
              class="cursor-pointer"
              @click="go(`/agent/runs/${run.id}`)"
            >
              <td class="font-weight-medium">
                {{ run.id }}
              </td><td>{{ run.agentName }}</td><td>{{ run.question }}</td><td>{{ run.tokens.toLocaleString() }}</td><td>{{ money(run.costUsd) }}</td><td>
                <VChip
                  size="small"
                  :color="run.status === 'succeeded' ? 'success' : run.status === 'failed' ? 'error' : 'info'"
                >
                  {{ run.status }}
                </VChip>
              </td>
            </tr>
          </tbody>
        </VTable>
      </VCard>
    </template>
    <template v-else-if="props.mode === 'run-detail' && currentRun">
      <VCard>
        <VCardItem><VCardTitle>{{ currentRun.id }} · {{ currentRun.question }}</VCardTitle><VCardSubtitle>{{ currentRun.agentName }} · {{ currentRun.tokens.toLocaleString() }} tokens · {{ money(currentRun.costUsd) }}</VCardSubtitle></VCardItem><VCardText>
          <VTimeline
            side="end"
            density="compact"
          >
            <VTimelineItem
              v-for="step in steps"
              :key="step.id"
              :dot-color="step.kind === 'suggestion' ? 'warning' : 'primary'"
            >
              <div class="font-weight-medium">
                {{ step.title }}
              </div><div class="text-body-2">
                {{ step.detail }}
              </div><div
                v-if="step.input"
                class="text-caption mt-2"
              >
                {{ t('agentModule.input') }}：{{ step.input }}
              </div><div
                v-if="step.output"
                class="text-caption"
              >
                {{ t('agentModule.output') }}：{{ step.output }}
              </div><VChip
                v-if="step.redacted"
                size="x-small"
                class="mt-2"
                variant="tonal"
              >
                {{ t('agentModule.redacted') }}
              </VChip>
            </VTimelineItem>
          </VTimeline>
        </VCardText>
      </VCard>
    </template>
    <template v-else-if="props.mode === 'knowledge'">
      <VCard>
        <VCardItem><VCardTitle>{{ t('agentModule.knowledge.baseName') }}</VCardTitle><VCardSubtitle>{{ t('agentModule.knowledge.baseDescription') }}</VCardSubtitle></VCardItem><VTable>
          <thead><tr><th>{{ t('agentModule.document') }}</th><th>{{ t('agentModule.format') }}</th><th>Chunks</th><th>{{ t('common.status') }}</th></tr></thead><tbody>
            <tr
              v-for="doc in docs"
              :key="doc.id"
              class="cursor-pointer"
              @click="go(`/agent/knowledge/${doc.knowledgeBaseId}`)"
            >
              <td>{{ doc.name }}</td><td>{{ doc.format }}</td><td>{{ doc.chunks }}</td><td>
                <VChip
                  size="small"
                  :color="doc.status === 'indexed' ? 'success' : 'warning'"
                >
                  {{ doc.status }}
                </VChip>
              </td>
            </tr>
          </tbody>
        </VTable>
      </VCard>
    </template>
    <template v-else-if="props.mode === 'knowledge-detail'">
      <VCard>
        <VCardItem><VCardTitle>{{ t('agentModule.knowledge.detailTitle') }}</VCardTitle><VCardSubtitle>{{ t('agentModule.knowledge.chunksHint') }}</VCardSubtitle></VCardItem><VCardText>
          <VExpansionPanels>
            <VExpansionPanel
              v-for="doc in docs"
              :key="doc.id"
              :title="doc.name"
            >
              <VExpansionPanelText>
                <p>{{ t('agentModule.knowledge.chunkPreview') }}</p><VChip
                  size="small"
                  variant="tonal"
                >
                  {{ doc.chunks }} chunks
                </VChip>
              </VExpansionPanelText>
            </VExpansionPanel>
          </VExpansionPanels>
        </VCardText>
      </VCard>
    </template>
    <template v-else-if="props.mode === 'prompts'">
      <VRow>
        <VCol
          cols="12"
          md="7"
        >
          <VCard>
            <VTable>
              <thead><tr><th>{{ t('agentModule.version') }}</th><th>{{ t('agentModule.createdAt') }}</th><th>{{ t('agentModule.author') }}</th><th>{{ t('agentModule.hash') }}</th><th>{{ t('common.status') }}</th></tr></thead><tbody>
                <tr
                  v-for="prompt in prompts"
                  :key="prompt.id"
                  class="cursor-pointer"
                  @click="selectedPrompt = prompt"
                >
                  <td>{{ prompt.version }}</td><td>{{ prompt.createdAt }}</td><td>{{ prompt.author }}</td><td class="text-caption">
                    {{ prompt.hash }}
                  </td><td>
                    <VChip
                      size="small"
                      :color="prompt.active ? 'success' : 'default'"
                    >
                      {{ prompt.active ? t('agentModule.activeVersion') : t('agentModule.archived') }}
                    </VChip>
                  </td>
                </tr>
              </tbody>
            </VTable>
          </VCard>
        </VCol><VCol
          cols="12"
          md="5"
        >
          <VCard>
            <VCardItem><VCardTitle>{{ t('agentModule.compare') }}</VCardTitle></VCardItem><VCardText>
              <VTextarea
                :model-value="selectedPrompt?.content ?? prompts[0]?.content"
                readonly
                rows="8"
              /><VAlert
                type="info"
                variant="tonal"
              >
                {{ t('agentModule.diffHint') }}
              </VAlert>
            </VCardText>
          </VCard>
        </VCol>
      </VRow>
    </template>
    <template v-else-if="props.mode === 'evals'">
      <VRow>
        <VCol
          v-for="item in evalRuns"
          :key="item.id"
          cols="12"
          md="6"
        >
          <VCard class="h-100">
            <VCardItem>
              <VCardTitle>{{ item.name }}</VCardTitle><VCardSubtitle>{{ item.model }} · {{ item.createdAt }}</VCardSubtitle><template #append>
                <VChip
                  size="small"
                  :color="item.status === 'passed' ? 'success' : 'warning'"
                >
                  {{ item.status }}
                </VChip>
              </template>
            </VCardItem><VCardText>
              <div class="d-flex align-center gap-4">
                <div class="text-h3 text-primary">
                  {{ item.passRate }}%
                </div><div class="flex-grow-1">
                  <VProgressLinear
                    :model-value="item.passRate"
                    color="primary"
                    rounded
                    height="10"
                  /><div class="text-caption mt-2">
                    {{ item.passed }}/{{ item.total }} · baseline {{ item.baseline }}%
                  </div>
                </div>
              </div><VBtn
                class="mt-4"
                variant="text"
                @click="go(`/agent/evals/${item.id}`)"
              >
                {{ t('common.view') }}
              </VBtn>
            </VCardText>
          </VCard>
        </VCol>
      </VRow>
    </template>
    <template v-else-if="props.mode === 'eval-detail' && currentEval">
      <VCard>
        <VCardItem><VCardTitle>{{ currentEval.name }} · {{ currentEval.passRate }}%</VCardTitle><VCardSubtitle>{{ currentEval.model }} · {{ currentEval.createdAt }}</VCardSubtitle></VCardItem><VTable>
          <thead><tr><th>{{ t('agentModule.case') }}</th><th>{{ t('agentModule.expected') }}</th><th>{{ t('agentModule.actual') }}</th><th>{{ t('common.status') }}</th></tr></thead><tbody>
            <tr
              v-for="item in evalCases"
              :key="item.id"
            >
              <td>{{ item.question }}</td><td>{{ item.expected }}</td><td>{{ item.actual }}</td><td>
                <VIcon
                  :color="item.passed ? 'success' : 'error'"
                  :icon="item.passed ? 'tabler-check' : 'tabler-x'"
                />
              </td>
            </tr>
          </tbody>
        </VTable>
      </VCard>
    </template>
    <template v-else-if="props.mode === 'usage'">
      <VRow>
        <VCol
          cols="12"
          md="4"
        >
          <VCard>
            <VCardItem><VCardTitle>{{ t('agentModule.usage.calls') }}</VCardTitle></VCardItem><VCardText>
              <div class="text-h3 text-primary">
                {{ usageCalls.length }}
              </div><div class="text-caption">
                {{ t('agentModule.usage.callsHint') }}
              </div>
            </VCardText>
          </VCard>
        </VCol><VCol
          cols="12"
          md="4"
        >
          <VCard>
            <VCardItem><VCardTitle>{{ t('agentModule.usage.tokens') }}</VCardTitle></VCardItem><VCardText>
              <div class="text-h3 text-primary">
                {{ usageCalls.reduce((sum, call) => sum + call.totalTokens, 0).toLocaleString() }}
              </div><VProgressLinear
                class="mt-4"
                :model-value="68"
                color="primary"
              /><div class="text-caption mt-2">
                68% {{ t('agentModule.usage.budget') }}
              </div>
            </VCardText>
          </VCard>
        </VCol><VCol
          cols="12"
          md="4"
        >
          <VCard>
            <VCardItem><VCardTitle>{{ t('agentModule.usage.cost') }}</VCardTitle></VCardItem><VCardText>
              <div class="text-h3 text-primary">
                {{ money(usageCalls.reduce((sum, call) => sum + call.costUsd, 0)) }}
              </div><VAlert
                type="warning"
                variant="tonal"
                class="mt-3"
              >
                {{ t('agentModule.usage.alert') }}
              </VAlert>
            </VCardText>
          </VCard>
        </VCol>
      </VRow><VCard class="mt-6">
        <VCardItem><VCardTitle>{{ t('agentModule.usage.chart') }}</VCardTitle></VCardItem><VCardText>
          <div
            v-for="call in usageCalls"
            :key="call.id"
            class="d-flex align-center gap-3 mb-4"
          >
            <div
              class="text-caption"
              style="width: 120px;"
            >
              {{ call.createdAt }}
            </div><VProgressLinear
              :model-value="Math.min(call.totalTokens / 40, 100)"
              color="primary"
              rounded
            /><div
              class="text-caption"
              style="width: 100px;"
            >
              {{ call.totalTokens }} tokens
            </div>
          </div>
        </VCardText>
      </VCard>
    </template>
    <template v-else-if="props.mode === 'usage-detail' && currentCall">
      <VCard>
        <VCardItem><VCardTitle>{{ currentCall.id }}</VCardTitle><VCardSubtitle>{{ currentCall.model }} · {{ currentCall.createdAt }}</VCardSubtitle></VCardItem><VCardText>
          <VRow>
            <VCol
              cols="6"
              md="3"
            >
              <div class="text-caption">
                Input
              </div><div class="text-h6">
                {{ currentCall.inputTokens }}
              </div>
            </VCol><VCol
              cols="6"
              md="3"
            >
              <div class="text-caption">
                Output
              </div><div class="text-h6">
                {{ currentCall.outputTokens }}
              </div>
            </VCol><VCol
              cols="6"
              md="3"
            >
              <div class="text-caption">
                Total
              </div><div class="text-h6">
                {{ currentCall.totalTokens }}
              </div>
            </VCol><VCol
              cols="6"
              md="3"
            >
              <div class="text-caption">
                Cost
              </div><div class="text-h6">
                {{ money(currentCall.costUsd) }}
              </div>
            </VCol>
          </VRow><VDivider class="my-4" /><VChip
            v-for="flag in currentCall.redactionFlags"
            :key="flag"
            class="me-2"
            variant="tonal"
          >
            redacted: {{ flag }}
          </VChip><VChip
            class="ms-2"
            :color="currentCall.injectionCheck === 'passed' ? 'success' : 'error'"
            variant="tonal"
          >
            injection check: {{ currentCall.injectionCheck }}
          </VChip>
        </VCardText>
      </VCard>
    </template>
    <template v-else-if="props.mode === 'deerflow'">
      <VRow>
        <VCol
          cols="12"
          md="5"
        >
          <VCard>
            <VCardItem><VCardTitle>{{ t('agentModule.deerflow.connection') }}</VCardTitle></VCardItem><VCardText>
              <VChip
                color="success"
                class="mb-4"
              >
                {{ t('agentModule.deerflow.mockConnected') }}
              </VChip><VTextField
                model-value="http://127.0.0.1:2026"
                label="Base URL"
                readonly
              /><VTextField
                model-value="v2.x"
                label="Version"
                readonly
              /><VSwitch
                :model-value="false"
                label="Enabled for local preview"
              />
            </VCardText>
          </VCard>
        </VCol><VCol
          cols="12"
          md="7"
        >
          <VCard>
            <VCardItem><VCardTitle>{{ t('agentModule.deerflow.setup') }}</VCardTitle></VCardItem><VCardText>
              <VStepper
                :items="[t('agentModule.deerflow.step1'), t('agentModule.deerflow.step2'), t('agentModule.deerflow.step3')]"
                hide-actions
              >
                <template #item.1>
                  <VAlert
                    type="info"
                    variant="tonal"
                  >
                    {{ t('agentModule.deerflow.step1Hint') }}
                  </VAlert>
                </template><template #item.2>
                  <VList>
                    <VListItem
                      title="/mcp/tools"
                      subtitle="CrossERP 只读工具清单"
                    /><VListItem
                      title="/mcp/ask"
                      subtitle="生成待审批建议的入口"
                    />
                  </VList>
                </template><template #item.3>
                  <VAlert
                    type="warning"
                    variant="tonal"
                  >
                    {{ t('agentModule.deerflow.keyHint') }}
                  </VAlert>
                </template>
              </VStepper>
            </VCardText>
          </VCard>
        </VCol>
      </VRow>
    </template>
  </div>
</template>
