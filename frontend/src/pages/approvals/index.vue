<script setup lang="ts">
import { PerfectScrollbar } from 'vue3-perfect-scrollbar'
import { decideApproval, fetchApprovals } from '@/api/approvals'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import { useSessionStore } from '@/stores/session'
import type { ApprovalItem, ApprovalStatus } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const session = useSessionStore()
const rows = ref<ApprovalItem[]>([])
const selected = ref<ApprovalItem | null>(null)
const drawer = ref(false)

const canDecide = computed(() => session.role === 'admin' || session.role === 'finance')

onMounted(async () => {
  rows.value = await fetchApprovals()
})

const columns = computed(() => [
  { key: 'title', title: t('approvals.detail') },
  { key: 'type', title: t('approvals.type') },
  { key: 'submitter', title: t('approvals.submitter') },
  { key: 'submittedAt', title: t('approvals.submittedAt') },
  { key: 'amount', title: t('common.amount'), align: 'end' as const },
  { key: 'status', title: t('common.status') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [{
  key: 'status',
  label: t('common.status'),
  items: (['pending', 'approved', 'rejected'] as ApprovalStatus[]).map(status => ({
    title: t(`approvals.${status}`),
    value: status,
  })),
}])

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
</script>

<template>
  <div>
    <VAlert
      v-if="!canDecide"
      type="warning"
      variant="tonal"
      class="mb-4"
    >
      {{ t('approvals.readonly') }}
    </VAlert>
    <ListPage
      storage-key="approvals"
      :title="t('approvals.title')"
      :subtitle="t('approvals.subtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      @open="open"
    >
      <template #widgets>
        <VRow class="mb-6">
          <VCol
            cols="12"
            sm="4"
          >
            <KpiCard
              title="待审批"
              :value="String(rows.filter(item => item.status === 'pending').length)"
              icon="tabler-clock"
              color="warning"
            />
          </VCol>
          <VCol
            cols="12"
            sm="4"
          >
            <KpiCard
              title="今日已批"
              :value="String(rows.filter(item => item.status === 'approved').length)"
              icon="tabler-check"
              color="success"
            />
          </VCol>
          <VCol
            cols="12"
            sm="4"
          >
            <KpiCard
              title="驳回"
              :value="String(rows.filter(item => item.status === 'rejected').length)"
              icon="tabler-x"
              color="error"
            />
          </VCol>
        </VRow>
      </template>
      <template #item.amount="{ item }">
        <MoneyText
          :amount="item.amount"
          minor
          :currency="item.currency"
        />
      </template>
      <template #item.status="{ item }">
        <StatusChip
          domain="approval"
          :value="item.status"
        />
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
    </ListPage>

    <VNavigationDrawer
      v-model="drawer"
      data-allow-mismatch
      temporary
      location="end"
      :width="400"
      class="scrollable-content"
    >
      <AppDrawerHeaderSection
        :title="selected?.title || t('approvals.decide')"
        @cancel="drawer = false"
      />
      <VDivider />
      <PerfectScrollbar
        v-if="selected"
        :options="{ wheelPropagation: false }"
      >
        <VCard flat>
          <VCardText>
            <div class="text-caption text-medium-emphasis mb-4">
              {{ selected.submitter }} · {{ selected.submittedAt }}
            </div>
            <p>{{ selected.summary }}</p>
            <div class="text-h6 mb-2">
              <MoneyText
                :amount="selected.amount"
                :currency="selected.currency"
                minor
              />
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
                    <MoneyText
                      v-if="line.debit"
                      :amount="line.debit"
                      :currency="selected.currency"
                      minor
                    />
                    <span v-else>—</span>
                  </td>
                  <td class="text-end">
                    <MoneyText
                      v-if="line.credit"
                      :amount="line.credit"
                      :currency="selected.currency"
                      minor
                    />
                    <span v-else>—</span>
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
          </VCardText>
        </VCard>
      </PerfectScrollbar>
    </VNavigationDrawer>
  </div>
</template>
