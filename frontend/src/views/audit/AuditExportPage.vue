<script setup lang="ts">
import { fetchAuditEvents, recordAuditExport } from '@/api/audit-module'
import type { AuditEvent } from '@/types/entities'

const { t } = useI18n({ useScope: 'global' })
const events = ref<AuditEvent[]>([])
const range = ref(['2026-11-01', '2026-11-09'])
const exportFormat = ref<'json' | 'csv'>('json')

onMounted(async () => {
  events.value = await fetchAuditEvents()
})
function cancel() {
  return undefined
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
  await recordAuditExport(exportFormat.value, events.value.length)

  const manifest = { generatedAt: new Date().toISOString(), range: range.value, scope: 'business-audit', eventCount: events.value.length, hash: `demo-${events.value.length.toString(16).padStart(8, '0')}` }
  if (exportFormat.value === 'csv') {
    const rows = events.value.map(event => [event.id, event.at, event.actor, event.action, event.refType, event.refId, event.summary].map(value => `"${String(value).replaceAll('"', '""')}"`).join(','))

    download(['id,at,actor,action,refType,refId,summary', ...rows].join('\n'), 'crosserp-audit.csv', 'text/csv;charset=utf-8')
  }
  else {
    download(JSON.stringify({ manifest, events: events.value }, null, 2), 'crosserp-audit.json', 'application/json')
  }
}
</script>

<template>
  <FormPage
    :title="t('auditModule.export.title')"
    :subtitle="t('auditModule.export.hint')"
    @save="exportPack"
    @cancel="cancel"
  >
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
        <AppSelect
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
      {{ t('auditModule.export.manifest') }} · {{ events.length }} events
    </VAlert>
  </FormPage>
</template>
