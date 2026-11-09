<script setup lang="ts">
import { fetchAuditChain, fetchAuditEvents, recordAuditExport, verifyAuditChain } from '@/api/audit-module'
import { fetchSecurityEvents } from '@/api/agent-module'
import type { AuditChainEntry, SecurityEvent } from '@/types/agent-module'
import type { AuditEvent } from '@/types/entities'

const props = defineProps<{ mode: 'audit' | 'verify' | 'export' | 'security' }>()
const { t } = useI18n({ useScope: 'global' })
const events = ref<AuditEvent[]>([])
const chain = ref<AuditChainEntry[]>([])
const security = ref<SecurityEvent[]>([])
const actorFilter = ref('')
const actionFilter = ref('')
const entityFilter = ref('')
const tampered = ref(false)
const verified = ref<{ ok: boolean; brokenIndex: number }>({ ok: true, brokenIndex: -1 })
const range = ref(['2026-11-01', '2026-11-09'])
const exportFormat = ref<'json' | 'csv'>('json')

const title = computed(() => ({ audit: t('auditModule.title'), verify: t('auditModule.verify.title'), export: t('auditModule.export.title'), security: t('auditModule.security.title') }[props.mode]))
const filteredEvents = computed(() => events.value.filter(event => (!actorFilter.value || event.actor.includes(actorFilter.value)) && (!actionFilter.value || event.action.includes(actionFilter.value)) && (!entityFilter.value || event.refType.includes(entityFilter.value) || event.refId.includes(entityFilter.value))))

async function load() {
  events.value = await fetchAuditEvents()
  if (props.mode === 'verify')
    chain.value = await fetchAuditChain()
  if (props.mode === 'security')
    security.value = await fetchSecurityEvents()
}
onMounted(load)
watch(() => props.mode, load)

async function verify() {
  verified.value = await verifyAuditChain(tampered.value ? Math.min(1, events.value.length - 1) : -1)
}

function download(content: string, name: string, type: string) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')

  anchor.href = url
  anchor.download = name
  anchor.click()
  URL.revokeObjectURL(url)
}

async function exportPack() {
  await recordAuditExport(exportFormat.value, filteredEvents.value.length)

  const manifest = { generatedAt: new Date().toISOString(), range: range.value, scope: 'business-audit', eventCount: filteredEvents.value.length, hash: `demo-${filteredEvents.value.length.toString(16).padStart(8, '0')}` }
  if (exportFormat.value === 'csv') {
    const rows = filteredEvents.value.map(event => [event.id, event.at, event.actor, event.action, event.refType, event.refId, event.summary].map(value => `"${String(value).replaceAll('"', '""')}"`).join(','))

    download(['id,at,actor,action,refType,refId,summary', ...rows].join('\n'), 'crosserp-audit.csv', 'text/csv;charset=utf-8')
  }
  else {
    download(JSON.stringify({ manifest, events: filteredEvents.value }, null, 2), 'crosserp-audit.json', 'application/json')
  }
}
</script>

<template>
  <div>
    <div class="d-flex align-center justify-space-between mb-6 flex-wrap gap-3">
      <div>
        <h4 class="text-h4">
          {{ title }}
        </h4><p class="text-body-1 text-medium-emphasis mb-0">
          {{ t('auditModule.subtitle') }}
        </p>
      </div><VChip
        color="info"
        variant="tonal"
      >
        <VIcon
          start
          icon="tabler-shield-check"
        />{{ t('auditModule.demoLabel') }}
      </VChip>
    </div>
    <template v-if="props.mode === 'audit'">
      <VCard class="mb-5">
        <VCardText>
          <VRow>
            <VCol
              cols="12"
              md="3"
            >
              <AppTextField
                v-model="actorFilter"
                :label="t('auditModule.actor')"
              />
            </VCol><VCol
              cols="12"
              md="3"
            >
              <AppTextField
                v-model="actionFilter"
                :label="t('auditModule.action')"
              />
            </VCol><VCol
              cols="12"
              md="3"
            >
              <AppTextField
                v-model="entityFilter"
                :label="t('auditModule.entity')"
              />
            </VCol><VCol
              cols="12"
              md="3"
            >
              <div class="text-caption mb-2">
                {{ t('auditModule.date') }}
              </div><VChip variant="tonal">
                2026-11-01 → 2026-11-09
              </VChip>
            </VCol>
          </VRow>
        </VCardText>
      </VCard><VCard>
        <VTable>
          <thead><tr><th>{{ t('auditModule.time') }}</th><th>{{ t('auditModule.actor') }}</th><th>{{ t('auditModule.action') }}</th><th>{{ t('auditModule.entity') }}</th><th>{{ t('auditModule.summary') }}</th></tr></thead><tbody>
            <tr
              v-for="event in filteredEvents"
              :key="event.id"
            >
              <td>{{ event.at }}</td><td>{{ event.actor }}</td><td>
                <VChip
                  size="small"
                  variant="tonal"
                >
                  {{ event.action }}
                </VChip>
              </td><td>{{ event.refType }} / {{ event.refId }}</td><td>{{ event.summary }}</td>
            </tr>
          </tbody>
        </VTable>
      </VCard>
    </template>
    <template v-else-if="props.mode === 'verify'">
      <VCard class="mb-5">
        <VCardText class="d-flex align-center justify-space-between flex-wrap gap-3">
          <div>
            <div class="text-h6">
              {{ t('auditModule.verify.chainTitle') }}
            </div><p class="text-body-2 text-medium-emphasis mb-0">
              {{ t('auditModule.verify.chainHint') }}
            </p>
          </div><div class="d-flex align-center gap-3">
            <VSwitch
              v-model="tampered"
              :label="t('auditModule.verify.tamper')"
              hide-details
            /><VBtn
              color="primary"
              @click="verify"
            >
              {{ t('auditModule.verify.action') }}
            </VBtn>
          </div>
        </VCardText>
      </VCard><VAlert
        v-if="verified.ok"
        type="success"
        variant="tonal"
        class="mb-5"
      >
        {{ t('auditModule.verify.ok') }}
      </VAlert><VAlert
        v-else
        type="error"
        variant="tonal"
        class="mb-5"
      >
        {{ t('auditModule.verify.broken', { index: verified.brokenIndex }) }}
      </VAlert><VCard>
        <VTable>
          <thead><tr><th>#</th><th>event</th><th>prev_hash</th><th>hash</th></tr></thead><tbody>
            <tr
              v-for="entry in chain"
              :key="entry.eventId"
            >
              <td>{{ entry.index }}</td><td>{{ entry.eventId }}</td><td class="text-caption">
                {{ entry.prevHash }}
              </td><td class="text-caption">
                {{ entry.hash }}
              </td>
            </tr>
          </tbody>
        </VTable>
      </VCard>
    </template>
    <template v-else-if="props.mode === 'export'">
      <VCard>
        <VCardItem><VCardTitle>{{ t('auditModule.export.title') }}</VCardTitle><VCardSubtitle>{{ t('auditModule.export.hint') }}</VCardSubtitle></VCardItem><VCardText>
          <VRow>
            <VCol
              cols="12"
              md="5"
            >
              <AppTextField
                v-model="range[0]"
                label="From"
                type="date"
              />
            </VCol><VCol
              cols="12"
              md="5"
            >
              <AppTextField
                v-model="range[1]"
                label="To"
                type="date"
              />
            </VCol><VCol
              cols="12"
              md="2"
            >
              <VSelect
                v-model="exportFormat"
                :items="['json', 'csv']"
                label="Format"
              />
            </VCol>
          </VRow><VAlert
            type="info"
            variant="tonal"
            class="my-4"
          >
            {{ t('auditModule.export.manifest') }} · {{ filteredEvents.length }} events
          </VAlert><VBtn
            color="primary"
            prepend-icon="tabler-download"
            @click="exportPack"
          >
            {{ t('auditModule.export.action') }}
          </VBtn>
        </VCardText>
      </VCard>
    </template>
    <template v-else>
      <VCard>
        <VCardItem><VCardTitle>{{ t('auditModule.security.title') }}</VCardTitle><VCardSubtitle>{{ t('auditModule.security.hint') }}</VCardSubtitle></VCardItem><VTable>
          <thead><tr><th>{{ t('auditModule.time') }}</th><th>{{ t('auditModule.actor') }}</th><th>{{ t('auditModule.security.event') }}</th><th>{{ t('auditModule.security.ip') }}</th><th>{{ t('auditModule.summary') }}</th></tr></thead><tbody>
            <tr
              v-for="event in security"
              :key="event.id"
            >
              <td>{{ event.at }}</td><td>{{ event.actor }}</td><td>
                <VChip
                  size="small"
                  :color="event.event.includes('failure') || event.event === 'denied_access' ? 'error' : 'success'"
                  variant="tonal"
                >
                  {{ event.event }}
                </VChip>
              </td><td>{{ event.ip }}</td><td>{{ event.summary }}</td>
            </tr>
          </tbody>
        </VTable>
      </VCard>
    </template>
  </div>
</template>
