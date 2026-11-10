<script setup lang="ts">
import { listReplenishmentPlans, runPlan } from '@/api/replenishment'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import type { ReplenishmentPlanSummary } from '@/types/replenishment'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const rows = ref<ReplenishmentPlanSummary[]>([])
const loading = ref(true)
const error = ref('')
const message = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await listReplenishmentPlans()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loading.value = false
  }
}
onMounted(load)

const columns = computed(() => [
  { key: 'versionNo', title: t('replenishment.version') },
  { key: 'runAt', title: t('replenishment.runAt') },
  { key: 'runBy', title: t('replenishment.runBy') },
  { key: 'methodVersion', title: t('replenishment.method') },
  { key: 'lineCount', title: t('replenishment.lineCount'), align: 'end' as const },
  { key: 'frozenCount', title: t('replenishment.frozenCount'), align: 'end' as const },
  { key: 'suggestedQty', title: t('replenishment.suggestedQty'), align: 'end' as const },
  { key: 'mustStockoutQty', title: t('replenishment.mustStockoutQty'), align: 'end' as const },
  { key: 'status', title: t('common.status') },
  { key: 'actions', title: t('common.actions') },
])

async function runNew() {
  try {
    await runPlan()
    message.value = t('replenishment.runSuccess')
    await load()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}

function open(row: ReplenishmentPlanSummary) {
  router.push({ path: `/inventory/replenishment/plans/${row.id}` })
}
</script>

<template>
  <div>
    <VAlert
      type="info"
      variant="tonal"
      class="mb-4"
    >
      {{ t('replenishment.demoHint') }} {{ t('replenishment.frozenHint') }}
    </VAlert>
    <VAlert
      v-if="message"
      type="success"
      variant="tonal"
      class="mb-4"
    >
      {{ message }}
    </VAlert>
    <ListPage
      storage-key="inventory-replenishment-plans"
      :title="t('replenishment.plansTitle')"
      :subtitle="t('replenishment.plansSubtitle')"
      :items="rows"
      :columns="columns"
      :loading="loading"
      :error="error"
      date-key="runAt"
      @retry="load"
      @open="open"
    >
      <template #actions>
        <PermissionGate permission="material_request:create">
          <VBtn
            color="primary"
            data-test="run-replenishment-plan-list"
            @click="runNew"
          >
            {{ t('replenishment.run') }}
          </VBtn>
        </PermissionGate>
      </template>
      <template #item.versionNo="{ item }">
        <span class="font-weight-medium">V{{ item.versionNo }}</span>
      </template>
      <template #item.runAt="{ item }">
        {{ item.runAt.slice(0, 16).replace('T', ' ') }}
      </template>
      <template #item.status="{ item }">
        <StatusChip
          domain="generic"
          :value="item.status"
        />
      </template>
      <template #item.actions="{ item }">
        <VBtn
          size="small"
          variant="text"
          :data-test="`open-replenishment-version-${item.id}`"
          @click="open(item)"
        >
          {{ t('replenishment.openVersion') }}
        </VBtn>
      </template>
    </ListPage>
  </div>
</template>
