<script setup lang="ts">
import { fetchAgentDefinitions, fetchAgentRuns, fetchChat } from '@/api/agent'
import { fetchAgentTasks, fetchEvalRuns, fetchKnowledgeDocuments, fetchPromptVersions, fetchUsageCalls } from '@/api/agent-module'
import ListPage from '@/components/biz/ListPage.vue'
import type { AgentDefinition, AgentRun, ChatThread } from '@/types/domain'
import type { AgentTask, EvalRun, KnowledgeDocument, PromptVersion, UsageCall } from '@/types/agent-module'

type ListMode = 'definitions' | 'tools' | 'threads' | 'tasks' | 'runs' | 'knowledge' | 'prompts' | 'evals' | 'usage'

const props = defineProps<{ mode: ListMode }>()
const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const loading = ref(true)
const definitions = ref<AgentDefinition[]>([])
const runs = ref<AgentRun[]>([])
const threads = ref<ChatThread[]>([])
const tasks = ref<AgentTask[]>([])
const docs = ref<KnowledgeDocument[]>([])
const prompts = ref<PromptVersion[]>([])
const evalRuns = ref<EvalRun[]>([])
const usageCalls = ref<UsageCall[]>([])

const title = computed(() => ({
  definitions: t('agentModule.definitions.title'),
  tools: t('agentModule.tools.title'),
  threads: t('agentModule.threads.title'),
  tasks: t('agentModule.tasks.title'),
  runs: t('agentModule.runs.title'),
  knowledge: t('agentModule.knowledge.title'),
  prompts: t('agentModule.prompts.title'),
  evals: t('agentModule.evals.title'),
  usage: t('agentModule.usage.title'),
}[props.mode]))

async function load() {
  loading.value = true
  try {
    if (props.mode === 'definitions' || props.mode === 'tools')
      definitions.value = await fetchAgentDefinitions()
    if (props.mode === 'runs')
      runs.value = await fetchAgentRuns()
    if (props.mode === 'threads')
      threads.value = (await fetchChat()).threads
    if (props.mode === 'tasks')
      tasks.value = await fetchAgentTasks()
    if (props.mode === 'knowledge')
      docs.value = await fetchKnowledgeDocuments()
    if (props.mode === 'prompts')
      prompts.value = await fetchPromptVersions()
    if (props.mode === 'evals')
      evalRuns.value = await fetchEvalRuns()
    if (props.mode === 'usage')
      usageCalls.value = await fetchUsageCalls()
  }
  finally { loading.value = false }
}

onMounted(load)
watch(() => props.mode, load)

const money = (value: number) => `$${value.toFixed(3)}`
const open = (path: string) => router.push(path).catch(() => undefined)

const runColumns = computed(() => [
  { key: 'agentName', title: t('runs.agent') },
  { key: 'startedAt', title: t('runs.startedAt') },
  { key: 'durationMs', title: t('runs.duration') },
  { key: 'tokens', title: t('runs.tokens') },
  { key: 'costUsd', title: t('runs.cost') },
  { key: 'status', title: t('common.status') },
  { key: 'question', title: t('runs.question') },
])

const taskColumns = computed(() => [{ key: 'name', title: t('agentModule.tasks.title') }, { key: 'schedule', title: t('agentModule.tasks.schedule') }, { key: 'status', title: t('common.status') }, { key: 'nextRun', title: t('agentModule.nextRun') }])
const docColumns = computed(() => [{ key: 'name', title: t('agentModule.document') }, { key: 'format', title: t('agentModule.format') }, { key: 'chunks', title: 'Chunks' }, { key: 'status', title: t('common.status') }])
const evalColumns = computed(() => [{ key: 'name', title: t('agentModule.evals.title') }, { key: 'model', title: t('agentModule.model') }, { key: 'createdAt', title: t('agentModule.createdAt') }, { key: 'passRate', title: t('agentModule.evals.passRate') }, { key: 'status', title: t('common.status') }])
const usageColumns = computed(() => [{ key: 'createdAt', title: t('agentModule.createdAt') }, { key: 'model', title: t('agentModule.model') }, { key: 'totalTokens', title: t('agentModule.tokens') }, { key: 'costUsd', title: t('agentModule.cost') }, { key: 'injectionCheck', title: t('common.status') }])
const threadColumns = computed(() => [{ key: 'title', title: t('agentModule.threads.title') }, { key: 'updatedAt', title: t('agentModule.createdAt') }])
const promptColumns = computed(() => [{ key: 'version', title: t('agentModule.version') }, { key: 'name', title: t('agentModule.prompts.title') }, { key: 'createdAt', title: t('agentModule.createdAt') }, { key: 'author', title: t('agentModule.author') }, { key: 'active', title: t('common.status') }])
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
      </div>
      <VChip
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
      v-if="props.mode === 'tools'"
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
                  {{ agent.status }}
                </VChip>
              </template>
            </VCardItem><VCardText>
              <p>{{ agent.duty }}</p><div class="text-body-2">
                {{ t('agentModule.model') }}：{{ agent.model }}
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
                @click="open(`/agent/definitions/${agent.id}`)"
              >
                {{ t('common.view') }}
              </VBtn>
            </VCardText>
          </VCard>
        </VCol>
      </VRow>
    </template>
    <ListPage
      v-else-if="props.mode === 'runs'"
      storage-key="agent-runs"
      :title="title"
      :subtitle="t('agentModule.subtitle')"
      :items="runs"
      :columns="runColumns"
      @open="open(`/agent/runs/${$event.id}`)"
    >
      <template #item.durationMs="{ item }">
        {{ (item.durationMs / 1000).toFixed(1) }} s
      </template><template #item.costUsd="{ item }">
        {{ money(item.costUsd) }}
      </template><template #item.status="{ item }">
        <StatusChip
          domain="generic"
          :value="item.status"
        />
      </template>
    </ListPage>
    <ListPage
      v-else-if="props.mode === 'tasks'"
      storage-key="agent-tasks"
      :title="title"
      :items="tasks"
      :columns="taskColumns"
      @open="open(`/agent/tasks/${$event.id}`)"
    >
      <template #item.status="{ item }">
        <VChip
          size="small"
          :color="item.status === 'active' ? 'success' : 'warning'"
        >
          {{ item.status }}
        </VChip>
      </template>
    </ListPage>
    <ListPage
      v-else-if="props.mode === 'knowledge'"
      storage-key="agent-knowledge"
      :title="title"
      :items="docs"
      :columns="docColumns"
      @open="open(`/agent/knowledge/${$event.knowledgeBaseId}`)"
    >
      <template #item.status="{ item }">
        <VChip
          size="small"
          :color="item.status === 'indexed' ? 'success' : 'warning'"
        >
          {{ item.status }}
        </VChip>
      </template>
    </ListPage>
    <ListPage
      v-else-if="props.mode === 'evals'"
      storage-key="agent-evals"
      :title="title"
      :items="evalRuns"
      :columns="evalColumns"
      @open="open(`/agent/evals/${$event.id}`)"
    >
      <template #item.passRate="{ item }">
        {{ Math.round(item.passRate * 100) }}%
      </template><template #item.status="{ item }">
        <VChip
          size="small"
          :color="item.status === 'passed' ? 'success' : item.status === 'warning' ? 'warning' : 'info'"
        >
          {{ item.status }}
        </VChip>
      </template>
    </ListPage>
    <ListPage
      v-else-if="props.mode === 'usage'"
      storage-key="agent-usage"
      :title="title"
      :items="usageCalls"
      :columns="usageColumns"
      @open="open(`/agent/usage/${$event.id}`)"
    >
      <template #item.costUsd="{ item }">
        {{ money(item.costUsd) }}
      </template><template #item.injectionCheck="{ item }">
        <VChip
          size="small"
          :color="item.injectionCheck === 'passed' ? 'success' : 'error'"
        >
          {{ item.injectionCheck }}
        </VChip>
      </template>
    </ListPage>
    <ListPage
      v-else-if="props.mode === 'threads'"
      storage-key="agent-threads"
      :title="title"
      :items="threads"
      :columns="threadColumns"
      @open="open('/agent/chat')"
    />
    <ListPage
      v-else-if="props.mode === 'prompts'"
      storage-key="agent-prompts"
      :title="title"
      :items="prompts"
      :columns="promptColumns"
    >
      <template #item.active="{ item }">
        <VChip
          size="small"
          :color="item.active ? 'success' : 'default'"
        >
          {{ item.active ? t('agentModule.activeVersion') : t('agentModule.archived') }}
        </VChip>
      </template>
    </ListPage>
    <VCard v-else-if="props.mode === 'tools'">
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
  </div>
</template>
