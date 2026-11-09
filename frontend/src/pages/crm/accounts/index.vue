<script setup lang="ts">
import { fetchAccounts } from '@/api/crm'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import type { CrmAccount } from '@/types/domain'
import { formatInteger } from '@/utils/format'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const rows = ref<CrmAccount[]>([])

onMounted(async () => {
  rows.value = await fetchAccounts()
})

const columns = computed(() => [
  { key: 'name', title: t('crm.name') },
  { key: 'type', title: t('crm.type') },
  { key: 'country', title: t('crm.country') },
  { key: 'owner', title: t('crm.owner') },
  { key: 'pipeline', title: t('crm.pipeline'), align: 'end' as const },
  { key: 'orders', title: t('crm.orders'), align: 'end' as const },
  { key: 'status', title: t('common.status') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [
  {
    key: 'type',
    label: t('crm.type'),
    items: [...new Set(rows.value.map(item => item.type))].map(name => ({ title: name, value: name })),
  },
  {
    key: 'country',
    label: t('crm.country'),
    items: [...new Set(rows.value.map(item => item.country))].map(name => ({ title: name, value: name })),
  },
])

function open(row: CrmAccount) {
  router.push({ path: `/crm/accounts/${row.id}` })
}
</script>

<template>
  <ListPage
    storage-key="crm-accounts"
    :title="t('crm.title')"
    :subtitle="t('crm.subtitle')"
    :items="rows"
    :columns="columns"
    :filters="filters"
    @open="open"
  >
    <template #item.name="{ item }">
      <div class="font-weight-medium">
        {{ item.name }}
      </div>
      <div class="d-flex flex-wrap gap-1 mt-1">
        <VChip
          v-for="tag in item.tags"
          :key="tag"
          size="x-small"
          variant="tonal"
        >
          {{ tag }}
        </VChip>
      </div>
    </template>
    <template #item.pipeline="{ item }">
      <MoneyText
        :amount="item.pipeline"
        :currency="item.currency"
      />
    </template>
    <template #item.orders="{ item }">
      {{ formatInteger(item.orders) }}
    </template>
    <template #item.status="{ item }">
      <StatusChip
        domain="crm"
        :value="item.status"
      />
    </template>
    <template #item.actions="{ item }">
      <VBtn
        size="small"
        variant="text"
        :to="{ path: `/crm/accounts/${item.id}` }"
      >
        {{ t('common.view') }}
      </VBtn>
    </template>
  </ListPage>
</template>
