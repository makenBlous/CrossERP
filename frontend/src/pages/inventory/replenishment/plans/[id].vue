<script setup lang="ts">
import { approveFactor, convertPlanLine, freezePlanLine, getReplenishmentPlanById, listDemandFactors, proposeFactor } from '@/api/replenishment'
import DetailPage from '@/components/biz/DetailPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { readParam } from '@/utils/route-param'
import type { ReplenishmentLineType, ReplenishmentPlan, ReplenishmentPlanLine } from '@/types/replenishment'

const { t } = useI18n({ useScope: 'global' })
const route = useRoute()
const plan = ref<ReplenishmentPlan | null>(null)
const factors = ref<Awaited<ReturnType<typeof listDemandFactors>>>([])
const loading = ref(true)
const error = ref('')
const message = ref('')
const factorValue = ref('1.00')
const selectedSku = ref('NW-TENT-2P-OLV')
const selectedKind = ref<'season' | 'promo'>('season')

const planId = computed(() => readParam(route.params, 'id'))

const lineHeaders = computed(() => [
  { title: t('inventory.sku'), key: 'internalSku' },
  { title: t('replenishment.lineType'), key: 'lineType' },
  { title: t('replenishment.warehouse'), key: 'warehouseName' },
  { title: t('replenishment.suggestedQty'), key: 'suggestedQty' },
  { title: t('replenishment.delta'), key: 'deltaQty' },
  { title: t('replenishment.mustStockoutQty'), key: 'mustStockoutQty' },
  { title: t('common.status'), key: 'status' },
  { title: t('common.actions'), key: 'actions', sortable: false },
])

const factorHeaders = computed(() => [
  { title: 'SKU', key: 'internalSku' },
  { title: '类型', key: 'kind' },
  { title: '系数', key: 'factor' },
  { title: '来源', key: 'origin' },
  { title: '状态', key: 'status' },
  { title: '操作', key: 'actions', sortable: false },
])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const value = await getReplenishmentPlanById(planId.value)
    if (!value)
      throw new Error(t('replenishment.missing'))
    plan.value = value
    factors.value = await listDemandFactors()
  }
  catch (err) { error.value = err instanceof Error ? err.message : t('foundation.errorTitle') }
  finally { loading.value = false }
}
onMounted(load)

function lineTypeLabel(value: ReplenishmentLineType) {
  return value === 'buy' ? t('replenishment.buy') : value === 'ship_fba' ? t('replenishment.shipFba') : t('replenishment.shipOverseas')
}

function statusOf(line: ReplenishmentPlanLine) {
  return line.convertedDraftId ? 'converted' : line.frozen ? 'confirmed' : 'calculated'
}

function channelLabel(channel: 'sea' | 'air') {
  return channel === 'sea' ? '海运' : '空运'
}

async function toggleFreeze(line: ReplenishmentPlanLine) {
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

async function submitFactor() {
  try {
    await proposeFactor(selectedSku.value, selectedKind.value, factorValue.value)
    message.value = '需求系数已提交，等待运营主管审批。'
    factors.value = await listDemandFactors()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}

async function approve(id: string) {
  try {
    await approveFactor(id)
    message.value = '需求系数已批准，下次运行才进入公式。'
    factors.value = await listDemandFactors()
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
      {{ t('replenishment.detailSubtitle') }} {{ t('replenishment.stockoutHint') }} {{ t('replenishment.selfApprovePurchase') }}
    </VAlert>
    <VAlert
      v-if="message"
      type="success"
      variant="tonal"
      class="mb-4"
    >
      {{ message }}
    </VAlert>
    <VProgressLinear
      v-if="loading"
      indeterminate
      class="mb-4"
    />
    <ErrorState
      v-else-if="error"
      :text="error"
      @retry="load"
    />
    <DetailPage
      v-else-if="plan"
      :title="`${t('replenishment.detailTitle')} · V${plan.versionNo}`"
      :subtitle="`${plan.runBy} · ${plan.runAt.slice(0, 16).replace('T', ' ')} · ${plan.note}`"
      domain="generic"
      :status="plan.status"
      :timeline="[{ id: 'run', at: plan.runAt.slice(0, 16).replace('T', ' '), title: t('replenishment.run'), detail: `${plan.methodVersion} / ${plan.weightVersion}`, actor: plan.runBy }]"
    >
      <template #actions>
        <VBtn
          :to="{ path: '/inventory/replenishment/plans' }"
          variant="tonal"
        >
          {{ t('replenishment.plansTitle') }}
        </VBtn>
      </template>
      <VCard class="mb-6">
        <VCardItem><VCardTitle>{{ t('replenishment.formula') }}</VCardTitle></VCardItem>
        <VCardText>
          <VRow>
            <VCol
              cols="12"
              sm="4"
            >
              <div class="text-caption">
                {{ t('replenishment.method') }}
              </div><div class="font-weight-medium">
                {{ plan.methodVersion }}
              </div>
            </VCol>
            <VCol
              cols="12"
              sm="4"
            >
              <div class="text-caption">
                {{ t('replenishment.weight') }}
              </div><div class="font-weight-medium">
                {{ plan.weightVersion }}
              </div>
            </VCol>
            <VCol
              cols="12"
              sm="4"
            >
              <div class="text-caption">
                {{ t('replenishment.weights') }}
              </div><div class="font-weight-medium">
                SCALE=10000
              </div>
            </VCol>
          </VRow>
        </VCardText>
      </VCard>
      <VCard class="mb-6">
        <VCardItem><VCardTitle>{{ t('replenishment.lineCount') }}（{{ plan.lines.length }}）</VCardTitle></VCardItem>
        <VDataTable
          :headers="lineHeaders"
          :items="plan.lines"
          item-value="id"
          density="comfortable"
          hide-default-footer
          class="text-no-wrap"
        >
          <template #item.internalSku="{ item }">
            <div class="font-weight-medium">
              {{ item.internalSku }}
            </div>
            <div class="text-caption">
              {{ item.skuTitle }}
            </div>
          </template>
          <template #item.lineType="{ item }">
            {{ lineTypeLabel(item.lineType) }} · {{ channelLabel(item.channel) }}
          </template>
          <template #item.suggestedQty="{ item }">
            <span class="font-weight-medium">{{ item.suggestedQty }}</span>
            <VChip
              v-if="item.cappedBy.length"
              size="x-small"
              color="warning"
              class="ms-2"
            >
              {{ item.cappedBy.join('；') }}
            </VChip>
          </template>
          <template #item.deltaQty="{ item }">
            <span :class="item.deltaQty < 0 ? 'text-error' : 'text-success'">
              {{ item.deltaQty > 0 ? '+' : '' }}{{ item.deltaQty }}
            </span>
          </template>
          <template #item.mustStockoutQty="{ item }">
            <VChip
              v-if="item.mustStockoutQty"
              color="error"
              size="small"
            >
              {{ item.mustStockoutQty }}
            </VChip>
            <span v-else>0</span>
          </template>
          <template #item.status="{ item }">
            <StatusChip
              domain="generic"
              :value="statusOf(item)"
            />
            <div
              v-if="item.convertedDraftId"
              class="text-caption mt-1"
            >
              {{ t('replenishment.sourceDraft') }}：{{ item.convertedDraftId }}
            </div>
          </template>
          <template #item.actions="{ item }">
            <PermissionGate permission="material_request:write">
              <VBtn
                size="small"
                variant="text"
                :data-test="`detail-freeze-${item.id}`"
                @click="toggleFreeze(item)"
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
                :data-test="`detail-draft-${item.id}`"
                @click="draft(item)"
              >
                {{ t('replenishment.draftRequest') }}
              </VBtn>
            </PermissionGate>
          </template>
        </VDataTable>
      </VCard>
      <VCard class="mb-6">
        <VCardItem><VCardTitle>{{ t('replenishment.supplySnapshot') }}</VCardTitle></VCardItem>
        <VCardText>
          <VRow
            v-for="line in plan.lines"
            :key="`${line.id}-supply`"
            class="mb-3"
          >
            <VCol
              cols="12"
              md="3"
            >
              <strong>{{ line.internalSku }}</strong>
              <div class="text-caption">
                {{ line.warehouseName }}
              </div>
            </VCol>
            <VCol
              cols="12"
              md="9"
            >
              <div class="d-flex flex-wrap gap-2">
                <VChip
                  v-for="bucket in line.supply"
                  :key="bucket.bucket"
                  size="small"
                  variant="tonal"
                >
                  {{ bucket.label }} {{ bucket.qty }} · {{ bucket.etaDate }}
                </VChip>
              </div>
            </VCol>
          </VRow>
        </VCardText>
      </VCard>
      <VCard>
        <VCardItem><VCardTitle>{{ t('replenishment.factor') }}</VCardTitle></VCardItem>
        <VCardText>
          <VAlert
            type="warning"
            variant="tonal"
            class="mb-4"
          >
            {{ t('replenishment.proposedFactor') }}。{{ t('replenishment.selfApprove') }}
          </VAlert>
          <VRow class="mb-4">
            <VCol
              cols="12"
              md="3"
            >
              <AppSelect
                v-model="selectedSku"
                :items="['NW-TENT-2P-OLV', 'NW-MAT-OLV']"
                :label="t('inventory.sku')"
              />
            </VCol>
            <VCol
              cols="12"
              md="3"
            >
              <AppSelect
                v-model="selectedKind"
                :items="[{ title: '季节', value: 'season' }, { title: '活动', value: 'promo' }]"
                :label="t('replenishment.factor')"
              />
            </VCol>
            <VCol
              cols="12"
              md="3"
            >
              <AppTextField
                v-model="factorValue"
                :label="t('replenishment.factorValue')"
              />
            </VCol>
            <VCol
              cols="12"
              md="3"
              class="d-flex align-end"
            >
              <PermissionGate permission="material_request:write">
                <VBtn
                  color="primary"
                  @click="submitFactor"
                >
                  {{ t('replenishment.proposeFactor') }}
                </VBtn>
              </PermissionGate>
            </VCol>
          </VRow>
          <VDataTable
            :headers="factorHeaders"
            :items="factors"
            item-value="id"
            density="compact"
            hide-default-footer
          >
            <template #item.kind="{ item }">
              {{ item.kind === 'season' ? '季节' : '活动' }}
            </template>
            <template #item.factor="{ item }">
              {{ (item.num / item.den).toFixed(2) }}x
            </template>
            <template #item.origin="{ item }">
              {{ item.origin === 'ai' ? 'AI 建议' : '人工' }} · {{ item.proposedByName }}
            </template>
            <template #item.status="{ item }">
              <StatusChip
                domain="generic"
                :value="item.status"
              />
            </template>
            <template #item.actions="{ item }">
              <PermissionGate permission="material_request:approve">
                <VBtn
                  v-if="item.status === 'proposed'"
                  size="small"
                  variant="text"
                  color="success"
                  @click="approve(item.id)"
                >
                  {{ t('replenishment.approveFactor') }}
                </VBtn>
              </PermissionGate>
            </template>
          </VDataTable>
        </VCardText>
      </VCard>
    </DetailPage>
  </div>
</template>
