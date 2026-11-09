<script setup lang="ts">
import { fetchAccount } from '@/api/crm'
import DetailPage from '@/components/biz/DetailPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import type { CrmAccountDetail } from '@/types/domain'

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

const tabs = computed(() => [
  { value: 'profile', title: t('crm.detail'), icon: 'tabler-user' },
  { value: 'contacts', title: t('crm.contacts'), icon: 'tabler-users' },
  { value: 'opportunities', title: t('crm.opportunities'), icon: 'tabler-briefcase' },
  { value: 'orders', title: t('crm.orders'), icon: 'tabler-receipt' },
  { value: 'tickets', title: t('crm.tickets'), icon: 'tabler-ticket' },
])

const related = computed(() => account.value?.tickets.map(item => ({
  id: item.id,
  type: t('crm.tickets'),
  label: item.subject,
})) ?? [])

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
      :to="{ path: '/crm/accounts' }"
    >
      {{ t('crm.title') }}
    </VBtn>
    <LoadingState v-if="!loaded" />
    <VAlert
      v-else-if="!account"
      type="warning"
      variant="tonal"
    >
      {{ t('crm.missing') }}
    </VAlert>
    <DetailPage
      v-else
      :title="account.name"
      :subtitle="`${account.type} · ${account.country} · ${account.owner}`"
      domain="crm"
      :status="account.status"
      :related="related"
    >
      <VTabs
        v-model="tab"
        class="v-tabs-pill mb-6"
      >
        <VTab
          v-for="item in tabs"
          :key="item.value"
          :value="item.value"
        >
          <VIcon
            :size="18"
            :icon="item.icon"
            class="me-1"
          />
          <span>{{ item.title }}</span>
        </VTab>
      </VTabs>
      <VWindow
        v-model="tab"
        class="disable-tab-transition"
        :touch="false"
      >
        <VWindowItem value="profile">
          <VCard>
            <VCardText>
              <p>{{ account.note }}</p>
              <div class="mb-2">
                {{ t('crm.website') }}：{{ account.website }}
              </div>
              <div class="mb-2">
                {{ account.email }} · {{ account.phone }}
              </div>
              <div>
                {{ t('crm.pipeline') }}：
                <MoneyText
                  :amount="account.pipeline"
                  :currency="account.currency"
                />
              </div>
            </VCardText>
          </VCard>
        </VWindowItem>
        <VWindowItem value="contacts">
          <VCard>
            <VTable>
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
          </VCard>
        </VWindowItem>
        <VWindowItem value="opportunities">
          <VCard>
            <VTable>
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
                    <MoneyText
                      :amount="item.amount"
                      :currency="item.currency"
                    />
                  </td>
                </tr>
              </tbody>
            </VTable>
          </VCard>
        </VWindowItem>
        <VWindowItem value="orders">
          <VCard>
            <VTable>
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
                  <td>
                    <VBtn
                      v-if="item.to"
                      variant="text"
                      size="small"
                      :to="item.to"
                      data-test="account-order-link"
                    >
                      {{ item.orderNo }}
                    </VBtn>
                    <span v-else>{{ item.orderNo }}</span>
                  </td>
                  <td>{{ item.date }}</td>
                  <td class="text-end">
                    <MoneyText
                      :amount="item.amount"
                      :currency="item.currency"
                    />
                  </td>
                </tr>
              </tbody>
            </VTable>
          </VCard>
        </VWindowItem>
        <VWindowItem value="tickets">
          <VCard>
            <VTable>
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
        </VWindowItem>
      </VWindow>
    </DetailPage>
  </div>
</template>
