<script setup lang="ts">
import { fetchAccounts } from '@/api/crm'
import type { CrmAccount } from '@/types/domain'
import { formatInteger, formatMoney } from '@/utils/format'

const { t } = useI18n({ useScope: 'global' })
const rows = ref<CrmAccount[]>([])
const keyword = ref('')

onMounted(async () => {
  rows.value = await fetchAccounts()
})

const filtered = computed(() => {
  const text = keyword.value.trim().toLowerCase()

  return rows.value.filter(item => `${item.name} ${item.country} ${item.type}`.toLowerCase().includes(text))
})

const headers = computed(() => [
  { title: t('crm.name'), key: 'name' },
  { title: t('crm.type'), key: 'type' },
  { title: t('crm.country'), key: 'country' },
  { title: t('crm.owner'), key: 'owner' },
  { title: t('crm.pipeline'), key: 'pipeline', align: 'end' as const },
  { title: t('crm.orders'), key: 'orders', align: 'end' as const },
  { title: t('common.status'), key: 'status' },
  { title: '', key: 'actions', sortable: false },
])
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        {{ t('crm.title') }}
      </h4>
      <p class="text-body-1 text-medium-emphasis mb-0">
        {{ t('crm.subtitle') }}
      </p>
    </div>
    <VCard>
      <VCardText>
        <AppTextField
          v-model="keyword"
          :label="t('crm.name')"
          style="max-width: 320px;"
        />
      </VCardText>
      <VDataTable
        :headers="headers"
        :items="filtered"
        :items-per-page="10"
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
          {{ formatMoney(item.pipeline, item.currency) }}
        </template>
        <template #item.orders="{ item }">
          {{ formatInteger(item.orders) }}
        </template>
        <template #item.actions="{ item }">
          <VBtn
            size="small"
            variant="text"
            :to="`/crm/accounts/${item.id}`"
          >
            {{ t('common.view') }}
          </VBtn>
        </template>
      </VDataTable>
    </VCard>
  </div>
</template>
