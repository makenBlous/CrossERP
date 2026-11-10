<script setup lang="ts">
import { approveLandedCostVoucher, fetchLandedCost, submitLandedCostApproval } from '@/api/fin-cost'
import { canPermission } from '@/api/mock-client'
import AuditActorId from '@/components/biz/AuditActorId.vue'
import DetailPage from '@/components/biz/DetailPage.vue'
import EmptyState from '@/components/biz/EmptyState.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import type { LandedCostVoucher } from '@/mocks/services/fin-cost'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const session = useSessionStore()
const { t } = useI18n({ useScope: 'global' })
const row = ref<LandedCostVoucher | null>(null)
const message = ref('')
const error = ref('')
const busy = ref(false)

function voucherId() {
  return String((route.params as Record<string, string | undefined>).id ?? '')
}

async function load() {
  try {
    row.value = await fetchLandedCost(voucherId())
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('finance.financeCost.actionFailed')
  }
}

onMounted(load)

const canSubmit = computed(() => Boolean(row.value && ['draft', 'rejected'].includes(row.value.status) && canPermission('landed_cost_voucher:submit')))
const canApprove = computed(() => Boolean(row.value && row.value.status === 'pending' && canPermission('landed_cost_voucher:approve') && row.value.submitterId !== session.userId))

async function run(action: 'submit' | 'approve') {
  if (!row.value)
    return
  busy.value = true
  message.value = ''
  error.value = ''
  try {
    row.value = action === 'submit'
      ? await submitLandedCostApproval(row.value.id)
      : await approveLandedCostVoucher(row.value.id)
    message.value = action === 'submit' ? t('finance.financeCost.submitSuccess') : t('finance.financeCost.approveSuccess')
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('finance.financeCost.actionFailed')
  }
  finally {
    busy.value = false
  }
}
</script>

<template>
  <DetailPage
    v-if="row"
    :title="row.no"
    :subtitle="`${row.period} · ${row.shipmentId}`"
    domain="voucher"
    :status="row.status"
    :timeline="row.timeline.map(item => ({ id: item.id, at: item.at, title: item.title, detail: item.detail, actor: item.actor }))"
  >
    <template #actions>
      <VBtn
        v-if="canSubmit"
        prepend-icon="tabler-send"
        :loading="busy"
        @click="run('submit')"
      >
        {{ t('finance.financeCost.submit') }}
      </VBtn>
      <VBtn
        v-if="canApprove"
        color="success"
        prepend-icon="tabler-check"
        :loading="busy"
        @click="run('approve')"
      >
        {{ t('finance.financeCost.approve') }}
      </VBtn>
    </template>

    <VAlert
      v-if="message"
      type="success"
      variant="tonal"
      class="mb-6"
    >
      {{ message }}
    </VAlert>
    <VAlert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-6"
    >
      {{ error }}
    </VAlert>
    <VAlert
      type="info"
      variant="tonal"
      class="mb-6"
    >
      {{ t('finance.financeCost.allocationRule') }}
    </VAlert>

    <VCard
      :title="t('finance.financeCost.allocationPreview')"
      class="mb-6"
    >
      <VTable>
        <thead>
          <tr>
            <th>{{ t('inventory.sku') }}</th>
            <th>{{ t('finance.financeCost.batch') }}</th>
            <th>{{ t('finance.financeCost.weight') }}</th>
            <th class="text-end">
              {{ t('finance.amount') }}
            </th>
            <th class="text-end">
              {{ t('finance.financeCost.toStock') }}
            </th>
            <th class="text-end">
              {{ t('finance.financeCost.toCogs') }}
            </th>
            <th>{{ t('finance.financeCost.tail') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="allocation in row.allocations"
            :key="allocation.id"
          >
            <td>{{ allocation.internalSku }}</td>
            <td>{{ allocation.batch }}</td>
            <td>{{ allocation.chargeableWeight.toLocaleString() }} g</td>
            <td class="text-end">
              <MoneyText
                :amount="allocation.amount"
                minor
                currency="CNY"
              />
            </td>
            <td class="text-end">
              <MoneyText
                :amount="allocation.toStock"
                minor
                currency="CNY"
              />
            </td>
            <td class="text-end">
              <MoneyText
                :amount="allocation.toCogs"
                minor
                currency="CNY"
              />
            </td>
            <td>
              <VChip
                v-if="allocation.tailFlag"
                size="small"
                color="warning"
                variant="tonal"
              >
                {{ t('finance.financeCost.tailRow') }}
              </VChip>
              <span v-else>—</span>
            </td>
          </tr>
        </tbody>
      </VTable>
      <VCardText class="d-flex flex-wrap gap-4 align-center">
        <span>{{ t('finance.financeCost.poolTotal') }}：<MoneyText
          :amount="row.poolAmount"
          minor
          currency="CNY"
        /></span>
        <span>{{ t('finance.financeCost.submitter') }}：<AuditActorId :actor-id="row.submitterId" /></span>
        <span v-if="row.approvedById">{{ t('finance.financeCost.approver') }}：<AuditActorId :actor-id="row.approvedById" /></span>
      </VCardText>
    </VCard>

    <VCard :title="t('finance.financeCost.calculationTitle')">
      <VCardText>
        <p class="mb-2">
          {{ t('finance.financeCost.calculationText') }}
        </p>
        <p class="mb-0 text-caption text-medium-emphasis">
          {{ t('finance.financeCost.accountingNotice') }}
        </p>
      </VCardText>
    </VCard>
  </DetailPage>
  <EmptyState
    v-else
    :title="t('finance.financeCost.notFound')"
    :text="t('finance.financeCost.notFoundText')"
    back-to="/finance/landed-costs"
  />
</template>
