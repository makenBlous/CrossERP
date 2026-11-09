<script setup lang="ts">
import { decideApproval, fetchApprovals } from '@/api/approvals'
import { useSessionStore } from '@/stores/session'
import type { ApprovalItem, ApprovalStatus } from '@/types/domain'
import { formatMoney } from '@/utils/format'

const { t } = useI18n({ useScope: 'global' })
const session = useSessionStore()
const rows = ref<ApprovalItem[]>([])
const selected = ref<ApprovalItem | null>(null)
const drawer = ref(false)

const canDecide = computed(() => session.role === 'admin' || session.role === 'finance')

onMounted(async () => {
  rows.value = await fetchApprovals()
})

const headers = computed(() => [
  { title: t('approvals.detail'), key: 'title' },
  { title: t('approvals.type'), key: 'type' },
  { title: t('approvals.submitter'), key: 'submitter' },
  { title: t('approvals.submittedAt'), key: 'submittedAt' },
  { title: t('common.amount'), key: 'amount', align: 'end' as const },
  { title: t('common.status'), key: 'status' },
  { title: t('common.actions'), key: 'actions', sortable: false },
])

function open(item: ApprovalItem) {
  selected.value = item
  drawer.value = true
}

async function decide(status: ApprovalStatus) {
  if (!selected.value || !canDecide.value || status === 'pending')
    return

  const next = await decideApproval(selected.value.id, status)

  if (next) {
    const index = rows.value.findIndex(item => item.id === next.id)

    if (index >= 0)
      rows.value[index] = next
  }
  drawer.value = false
}

function statusLabel(status: ApprovalStatus) {
  return t(`approvals.${status}`)
}

function statusColor(status: ApprovalStatus) {
  if (status === 'approved')
    return 'success'
  if (status === 'rejected')
    return 'error'

  return 'warning'
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        {{ t('approvals.title') }}
      </h4>
      <p class="text-body-1 text-medium-emphasis mb-0">
        {{ t('approvals.subtitle') }}
      </p>
    </div>
    <VAlert
      v-if="!canDecide"
      type="warning"
      variant="tonal"
      class="mb-4"
    >
      {{ t('approvals.readonly') }}
    </VAlert>
    <VCard>
      <VDataTable
        :headers="headers"
        :items="rows"
        :items-per-page="10"
      >
        <template #item.amount="{ item }">
          {{ formatMoney(item.amount, item.currency) }}
        </template>
        <template #item.status="{ item }">
          <VChip
            size="small"
            :color="statusColor(item.status)"
          >
            {{ statusLabel(item.status) }}
          </VChip>
        </template>
        <template #item.actions="{ item }">
          <VBtn
            size="small"
            variant="text"
            @click="open(item)"
          >
            {{ t('approvals.decide') }}
          </VBtn>
        </template>
      </VDataTable>
    </VCard>

    <VNavigationDrawer
      v-model="drawer"
      location="end"
      temporary
      width="420"
    >
      <div
        v-if="selected"
        class="pa-6"
      >
        <div class="text-h6 mb-1">
          {{ selected.title }}
        </div>
        <div class="text-caption text-medium-emphasis mb-4">
          {{ selected.submitter }} · {{ selected.submittedAt }}
        </div>
        <p>{{ selected.summary }}</p>
        <div class="text-h6 mb-2">
          {{ formatMoney(selected.amount, selected.currency) }}
        </div>
        <VTable
          v-if="selected.lines.length"
          density="compact"
          class="mb-4"
        >
          <thead>
            <tr>
              <th>{{ t('approvals.account') }}</th>
              <th class="text-end">
                {{ t('approvals.debit') }}
              </th>
              <th class="text-end">
                {{ t('approvals.credit') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="line in selected.lines"
              :key="line.account"
            >
              <td>{{ line.account }}</td>
              <td class="text-end">
                {{ line.debit || '—' }}
              </td>
              <td class="text-end">
                {{ line.credit || '—' }}
              </td>
            </tr>
          </tbody>
        </VTable>
        <div class="d-flex gap-3">
          <VBtn
            color="success"
            :disabled="!canDecide || selected.status !== 'pending'"
            @click="decide('approved')"
          >
            {{ t('approvals.approve') }}
          </VBtn>
          <VBtn
            color="error"
            variant="tonal"
            :disabled="!canDecide || selected.status !== 'pending'"
            @click="decide('rejected')"
          >
            {{ t('approvals.reject') }}
          </VBtn>
        </div>
      </div>
    </VNavigationDrawer>
  </div>
</template>
