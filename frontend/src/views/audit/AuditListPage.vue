<script setup lang="ts">
import { fetchAuditEvents } from '@/api/audit-module'
import { fetchSecurityEvents } from '@/api/agent-module'
import ListPage from '@/components/biz/ListPage.vue'
import type { AuditEvent } from '@/types/entities'
import type { SecurityEvent } from '@/types/agent-module'

const props = defineProps<{ mode: 'audit' | 'security' }>()
const { t } = useI18n({ useScope: 'global' })
const events = ref<AuditEvent[]>([])
const security = ref<SecurityEvent[]>([])
const loading = ref(true)
async function load() {
  loading.value = true
  try {
    if (props.mode === 'audit') {
      events.value = (await fetchAuditEvents()).map(event => ({
        ...event,
        actor: event.actorId ? event.actor : `${event.actor}（旧记录未留 ID）`,
        actorId: event.actorId ?? '旧记录未留 ID',
      }))
    }
    else {
      security.value = await fetchSecurityEvents()
    }
  }
  finally { loading.value = false }
}
onMounted(load)
watch(() => props.mode, load)

const eventColumns = computed(() => [{ key: 'at', title: t('auditModule.time') }, { key: 'actor', title: t('auditModule.actor') }, { key: 'actorId', title: '操作者 ID' }, { key: 'action', title: t('auditModule.action') }, { key: 'refType', title: t('auditModule.entity') }, { key: 'refId', title: 'ID' }, { key: 'summary', title: t('auditModule.summary') }])
const securityColumns = computed(() => [{ key: 'at', title: t('auditModule.time') }, { key: 'actor', title: t('auditModule.actor') }, { key: 'event', title: t('auditModule.security.event') }, { key: 'ip', title: t('auditModule.security.ip') }, { key: 'summary', title: t('auditModule.summary') }])
</script>

<template>
  <ListPage
    v-if="props.mode === 'audit'"
    storage-key="audit-events"
    :title="t('auditModule.title')"
    :subtitle="t('auditModule.subtitle')"
    :items="events"
    :columns="eventColumns"
    :loading="loading"
  >
    <template #item.action="{ item }">
      <VChip
        size="small"
        variant="tonal"
      >
        {{ item.action }}
      </VChip>
    </template>
  </ListPage>
  <ListPage
    v-else
    storage-key="security-events"
    :title="t('auditModule.security.title')"
    :subtitle="t('auditModule.security.hint')"
    :items="security"
    :columns="securityColumns"
    :loading="loading"
  >
    <template #item.event="{ item }">
      <VChip
        size="small"
        :color="item.event.includes('failure') || item.event === 'denied_access' ? 'error' : 'success'"
        variant="tonal"
      >
        {{ item.event }}
      </VChip>
    </template>
  </ListPage>
</template>
