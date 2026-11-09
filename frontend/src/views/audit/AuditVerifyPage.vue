<script setup lang="ts">
import { fetchAuditChain, verifyAuditChain } from '@/api/audit-module'
import type { AuditChainEntry } from '@/types/agent-module'

const { t } = useI18n({ useScope: 'global' })
const chain = ref<AuditChainEntry[]>([])
const tampered = ref(false)
const verified = ref({ ok: true, brokenIndex: -1 })

onMounted(async () => {
  chain.value = await fetchAuditChain()
})
async function verify() {
  verified.value = await verifyAuditChain(tampered.value ? Math.min(1, chain.value.length - 1) : -1)
}
</script>

<template>
  <div>
    <div class="d-flex align-center justify-space-between mb-6">
      <div>
        <h4 class="text-h4">
          {{ t('auditModule.verify.title') }}
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
    </div><VCard class="mb-5">
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
  </div>
</template>
