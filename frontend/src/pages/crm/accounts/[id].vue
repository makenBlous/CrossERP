<script setup lang="ts">
import { fetchAccount } from '@/api/crm'
import type { CrmAccountDetail } from '@/types/domain'
import { formatMoney } from '@/utils/format'

const route = useRoute()
const { t } = useI18n({ useScope: 'global' })
const account = ref<CrmAccountDetail | null>(null)
const loaded = ref(false)
const tab = ref('profile')

const accountId = computed(() => {
  const params = route.params as Record<string, string | string[] | undefined>
  const value = params.id

  return Array.isArray(value) ? value[0] ?? '' : value ?? ''
})

async function load() {
  loaded.value = false
  account.value = await fetchAccount(accountId.value)
  loaded.value = true
}

onMounted(load)
watch(accountId, load)
</script>

<template>
  <div>
    <VBtn
      variant="text"
      class="mb-4"
      prepend-icon="tabler-arrow-left"
      to="/crm/accounts"
    >
      {{ t('crm.title') }}
    </VBtn>
    <VAlert
      v-if="loaded && !account"
      type="warning"
      variant="tonal"
    >
      {{ t('crm.missing') }}
    </VAlert>
    <template v-else-if="account">
      <div class="d-flex flex-wrap justify-space-between gap-4 mb-4">
        <div>
          <h4 class="text-h4">
            {{ account.name }}
          </h4>
          <p class="text-body-1 text-medium-emphasis mb-0">
            {{ account.type }} · {{ account.country }} · {{ account.owner }}
          </p>
        </div>
        <VChip color="primary">
          {{ account.status }}
        </VChip>
      </div>
      <VTabs
        v-model="tab"
        class="mb-4"
      >
        <VTab value="profile">
          {{ t('crm.detail') }}
        </VTab>
        <VTab value="contacts">
          {{ t('crm.contacts') }}
        </VTab>
        <VTab value="opportunities">
          {{ t('crm.opportunities') }}
        </VTab>
        <VTab value="orders">
          {{ t('crm.orders') }}
        </VTab>
        <VTab value="tickets">
          {{ t('crm.tickets') }}
        </VTab>
      </VTabs>
      <VCard>
        <VCardText v-if="tab === 'profile'">
          <p>{{ account.note }}</p>
          <div class="mb-2">
            {{ t('crm.website') }}：{{ account.website }}
          </div>
          <div class="mb-2">
            {{ account.email }} · {{ account.phone }}
          </div>
          <div>{{ t('crm.pipeline') }}：{{ formatMoney(account.pipeline, account.currency) }}</div>
        </VCardText>
        <VTable v-else-if="tab === 'contacts'">
          <thead>
            <tr>
              <th>{{ t('crm.name') }}</th>
              <th>{{ t('crm.type') }}</th>
              <th>Email</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="person in account.contacts"
              :key="person.email"
            >
              <td>{{ person.name }}</td>
              <td>{{ person.title }}</td>
              <td>{{ person.email }}</td>
            </tr>
          </tbody>
        </VTable>
        <VTable v-else-if="tab === 'opportunities'">
          <thead>
            <tr>
              <th>{{ t('crm.name') }}</th>
              <th>{{ t('crm.stage') }}</th>
              <th class="text-end">
                {{ t('common.amount') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in account.opportunities"
              :key="item.name"
            >
              <td>{{ item.name }}</td>
              <td>{{ item.stage }}</td>
              <td class="text-end">
                {{ formatMoney(item.amount, item.currency) }}
              </td>
            </tr>
          </tbody>
        </VTable>
        <VTable v-else-if="tab === 'orders'">
          <thead>
            <tr>
              <th>{{ t('orders.orderNo') }}</th>
              <th>{{ t('orders.date') }}</th>
              <th class="text-end">
                {{ t('common.amount') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in account.relatedOrders"
              :key="item.orderNo"
            >
              <td>{{ item.orderNo }}</td>
              <td>{{ item.date }}</td>
              <td class="text-end">
                {{ formatMoney(item.amount, item.currency) }}
              </td>
            </tr>
          </tbody>
        </VTable>
        <VTable v-else>
          <thead>
            <tr>
              <th>ID</th>
              <th>{{ t('issues.summary') }}</th>
              <th>{{ t('common.status') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in account.tickets"
              :key="item.id"
            >
              <td>{{ item.id }}</td>
              <td>{{ item.subject }}</td>
              <td>{{ item.status }}</td>
            </tr>
          </tbody>
        </VTable>
      </VCard>
    </template>
  </div>
</template>
