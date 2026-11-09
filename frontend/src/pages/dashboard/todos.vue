<script setup lang="ts">
import { fetchTodos } from '@/api/dashboard'
import ListPage from '@/components/biz/ListPage.vue'
import type { TodoRow } from '@/types/domain'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const rows = ref<TodoRow[]>([])
const loading = ref(true)
const error = ref('')

const kindLabel = computed(() => ({
  approval: t('todos.approval'),
  alert: t('todos.alert'),
  exception: t('todos.exception'),
  import: t('todos.import'),
}))

const viewRows = computed(() => rows.value.map(item => ({
  ...item,
  kindLabel: kindLabel.value[item.kind as keyof typeof kindLabel.value] ?? item.kind,
})))

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchTodos()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loading.value = false
  }
}

onMounted(load)

function openRow(row: TodoRow) {
  router.push({ path: row.to })
}

const columns = computed(() => [
  { key: 'kindLabel', title: t('todos.kind') },
  { key: 'title', title: t('catalog.name') },
  { key: 'detail', title: t('orders.summary') },
  { key: 'at', title: t('orders.date') },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [{
  key: 'kindLabel',
  label: t('todos.kind'),
  items: Object.values(kindLabel.value).map(name => ({ title: name, value: name })),
}])
</script>

<template>
  <div>
    <ListPage
      storage-key="dashboard-todos"
      :title="t('todos.title')"
      :subtitle="t('todos.subtitle')"
      :items="viewRows"
      :columns="columns"
      :filters="filters"
      date-key="at"
      :loading="loading"
      :error="error"
      :batch-actions="[{ key: 'open', label: t('todos.jump') }]"
      @retry="load"
      @open="openRow"
      @batch="(_action, selected) => selected[0] && openRow(selected[0])"
    >
      <template #item.actions="{ item }">
        <VBtn
          size="small"
          variant="text"
          :to="{ path: item.to }"
        >
          {{ t('todos.jump') }}
        </VBtn>
      </template>
    </ListPage>
    <VCard class="mt-4">
      <VCardItem>
        <VCardTitle>{{ t('todos.budget') }}</VCardTitle>
      </VCardItem>
      <VCardText>
        <EmptyState :text="t('todos.budgetEmpty')" />
      </VCardText>
    </VCard>
  </div>
</template>
