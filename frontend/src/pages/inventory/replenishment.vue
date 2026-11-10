<script setup lang="ts">
import { convertPlanLine, freezePlanLine, getLatestReplenishmentPlan, runPlan } from '@/api/replenishment'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import type { ReplenishmentLineType, ReplenishmentPlan, ReplenishmentPlanLine } from '@/types/replenishment'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const plan = ref<ReplenishmentPlan | null>(null)
const loading = ref(true)
const error = ref('')
const message = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    plan.value = await getLatestReplenishmentPlan()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loading.value = false
  }
}
onMounted(load)

const rows = computed(() => plan.value?.lines ?? [])

const columns = computed(() => [
  { key: 'internalSku', title: t('inventory.sku') },
  { key: 'warehouseName', title: t('replenishment.warehouse') },
  { key: 'lineType', title: t('replenishment.lineType') },
  { key: 'availableOnHand', title: t('replenishment.available'), align: 'end' as const },
  { key: 'inTransitQty', title: t('replenishment.inTransit'), align: 'end' as const },
  { key: 'suggestedQty', title: t('replenishment.suggestedQty'), align: 'end' as const },
  { key: 'mustStockoutQty', title: t('replenishment.mustStockoutQty'), align: 'end' as const },
  { key: 'status', title: t('common.status') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [
  { key: 'lineType', label: t('replenishment.lineType'), items: (['buy', 'ship_fba', 'ship_overseas'] as ReplenishmentLineType[]).map(value => ({ title: lineTypeLabel(value), value })) },
  { key: 'frozen', label: t('replenishment.frozen'), items: [{ title: t('replenishment.frozen'), value: 'true' }, { title: t('replenishment.calculated'), value: 'false' }] },
])

function lineTypeLabel(value: ReplenishmentLineType) {
  return value === 'buy' ? t('replenishment.buy') : value === 'ship_fba' ? t('replenishment.shipFba') : t('replenishment.shipOverseas')
}

function statusOf(line: ReplenishmentPlanLine) {
  return line.convertedDraftId ? 'converted' : line.frozen ? 'confirmed' : 'calculated'
}
function openVersion() {
  if (plan.value)
    router.push({ path: `/inventory/replenishment/plans/${plan.value.id}` })
}
async function runNew() {
  try {
    plan.value = await runPlan()
    message.value = t('replenishment.runSuccess')
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}

async function freeze(line: ReplenishmentPlanLine) {
  if (!plan.value)
    return

  try {
    await freezePlanLine(plan.value.id, line.id, !line.frozen)
    message.value = t('replenishment.freezeSuccess')
    await load()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}

async function draft(line: ReplenishmentPlanLine) {
  if (!plan.value)
    return

  try {
    await convertPlanLine(plan.value.id, line.id)
    message.value = t('replenishment.draftSuccess')
    await load()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}
</script>

<template>
  <div>
    <VAlert
      type="info"
      variant="tonal"
      class="mb-4"
    >
      {{ t('replenishment.demoHint') }} {{ t('replenishment.noAutoOrder') }} {{ t('replenishment.selfApprovePurchase') }}
    </VAlert>
    <VAlert
      v-if="message"
      type="success"
      variant="tonal"
      closable
      class="mb-4"
      @click:close="message = ''"
    >
      {{ message }}
    </VAlert>
    <ListPage
      storage-key="inventory-replenishment-latest"
      :title="t('page.I13.name')"
      :subtitle="plan ? `${t('replenishment.version')} V${plan.versionNo} · ${plan.runAt.slice(0, 16).replace('T', ' ')}` : t('replenishment.detailSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      :loading="loading"
      :error="error"
      @retry="load"
    >
      <template #actions>
        <VBtn
          variant="tonal"
          data-test="open-latest-replenishment-version"
          @click="openVersion"
        >
          {{ t('replenishment.openVersion') }}
        </VBtn>
        <PermissionGate permission="material_request:create">
          <VBtn
            color="primary"
            data-test="run-replenishment-plan"
            @click="runNew"
          >
            {{ t('replenishment.run') }}
          </VBtn>
        </PermissionGate>
      </template>
      <template #item.internalSku="{ item }">
        <div class="font-weight-medium">
          {{ item.internalSku }}
        </div><div class="text-caption text-medium-emphasis">
          {{ item.skuTitle }}
        </div>
      </template>
      <template #item.lineType="{ item }">
        {{ lineTypeLabel(item.lineType) }}
      </template>
      <template #item.suggestedQty="{ item }">
        <span class="font-weight-medium">{{ item.suggestedQty }}</span><VChip
          v-if="item.cappedBy.length"
          size="x-small"
          color="warning"
          class="ms-2"
        >
          {{ t('replenishment.cappedBy') }}
        </VChip>
      </template>
      <template #item.mustStockoutQty="{ item }">
        <VChip
          v-if="item.mustStockoutQty"
          size="small"
          color="error"
        >
          {{ item.mustStockoutQty }}
        </VChip><span v-else>0</span>
      </template>
      <template #item.status="{ item }">
        <StatusChip
          domain="generic"
          :value="statusOf(item)"
        />
      </template>
      <template #item.actions="{ item }">
        <VBtn
          size="small"
          variant="text"
          :to="{ path: `/inventory/replenishment/plans/${plan?.id}` }"
        >
          {{ t('replenishment.openVersion') }}
        </VBtn>
        <PermissionGate permission="material_request:write">
          <VBtn
            size="small"
            variant="text"
            :data-test="`freeze-replenishment-${item.id}`"
            @click="freeze(item)"
          >
            {{ item.frozen ? t('replenishment.unfreeze') : t('replenishment.freeze') }}
          </VBtn>
        </PermissionGate>
        <PermissionGate permission="material_request:submit">
          <VBtn
            v-if="item.lineType === 'buy' && item.frozen && !item.convertedDraftId"
            size="small"
            variant="text"
            color="primary"
            :data-test="`draft-replenishment-${item.id}`"
            @click="draft(item)"
          >
            {{ t('replenishment.draftRequest') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
  </div>
</template>
