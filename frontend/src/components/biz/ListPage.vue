<script setup lang="ts" generic="T extends { id: string }">
export interface ListColumn {
  key: string
  title: string
  align?: 'start' | 'end' | 'center'
}

export interface ListSelectFilter {
  key: string
  label: string
  items: { title: string; value: string }[]
}

export interface ListBatchAction {
  key: string
  label: string
}

interface SavedView {
  id: string
  name: string
  keyword: string
  selects: Record<string, string>
  dateFrom: string
  dateTo: string
}

const props = withDefaults(defineProps<{
  storageKey: string
  title: string
  subtitle?: string
  items: T[]
  columns: ListColumn[]
  filters?: ListSelectFilter[]
  dateKey?: string
  loading?: boolean
  error?: string
  batchActions?: ListBatchAction[]
}>(), {
  subtitle: '',
  filters: () => [],
  dateKey: '',
  loading: false,
  error: '',
  batchActions: () => [],
})

const emit = defineEmits<{
  retry: []
  batch: [action: string, rows: T[]]
}>()

const { t } = useI18n({ useScope: 'global' })
const keyword = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const selects = reactive<Record<string, string>>({})
const hidden = ref<string[]>([])
const saved = ref<SavedView[]>([])
const selected = ref<string[]>([])
const saveOpen = ref(false)
const viewName = ref('')

const viewKey = computed(() => `crosserp-list-view:${props.storageKey}`)
const columnKey = computed(() => `crosserp-list-cols:${props.storageKey}`)

function readJson<TValue>(key: string, fallback: TValue): TValue {
  try {
    const raw = localStorage.getItem(key)

    return raw ? JSON.parse(raw) as TValue : fallback
  }
  catch {
    return fallback
  }
}

onMounted(() => {
  hidden.value = readJson(columnKey.value, [])
  saved.value = readJson(viewKey.value, [])
})

watch(() => props.filters, filters => {
  for (const filter of filters) {
    if (!(filter.key in selects))
      selects[filter.key] = 'all'
  }
}, { immediate: true })

const visibleColumns = computed(() => props.columns.filter(column => !hidden.value.includes(column.key)))

const headers = computed(() => visibleColumns.value.map(column => ({
  title: column.title,
  key: column.key,
  align: column.align,
  sortable: column.key !== 'actions',
})))

function cellText(item: T, key: string) {
  const value = (item as Record<string, unknown>)[key]

  if (value == null)
    return ''

  return String(value)
}

function rowDate(item: T) {
  if (!props.dateKey)
    return ''

  return cellText(item, props.dateKey).slice(0, 10)
}

const filtered = computed(() => props.items.filter(item => {
  const text = props.columns.map(column => cellText(item, column.key)).join(' ').toLowerCase()
  const keywordOk = text.includes(keyword.value.trim().toLowerCase())

  const selectOk = (props.filters ?? []).every(filter => {
    const chosen = selects[filter.key] || 'all'

    return chosen === 'all' || cellText(item, filter.key) === chosen
  })

  const date = rowDate(item)
  const fromOk = !dateFrom.value || !date || date >= dateFrom.value
  const toOk = !dateTo.value || !date || date <= dateTo.value

  return keywordOk && selectOk && fromOk && toOk
}))

function selectedId(value: unknown) {
  if (typeof value === 'string' || typeof value === 'number')
    return String(value)

  if (value && typeof value === 'object' && 'id' in value)
    return String((value as { id: string }).id)

  return ''
}

const selectedRows = computed(() => {
  const ids = new Set(selected.value.map(selectedId))

  return props.items.filter(item => ids.has(item.id))
})

function persistColumns() {
  localStorage.setItem(columnKey.value, JSON.stringify(hidden.value))
}

function toggleColumn(key: string) {
  if (hidden.value.includes(key))
    hidden.value = hidden.value.filter(item => item !== key)
  else if (visibleColumns.value.length > 1)
    hidden.value = [...hidden.value, key]

  persistColumns()
}

function persistViews() {
  localStorage.setItem(viewKey.value, JSON.stringify(saved.value))
}

function saveView() {
  const name = viewName.value.trim()

  if (!name)
    return

  saved.value = [...saved.value, {
    id: `${Date.now()}`,
    name,
    keyword: keyword.value,
    selects: { ...selects },
    dateFrom: dateFrom.value,
    dateTo: dateTo.value,
  }]
  persistViews()
  viewName.value = ''
  saveOpen.value = false
}

function applyView(view: SavedView) {
  keyword.value = view.keyword
  dateFrom.value = view.dateFrom
  dateTo.value = view.dateTo
  Object.assign(selects, view.selects)
}

function removeView(id: string) {
  saved.value = saved.value.filter(item => item.id !== id)
  persistViews()
}

function exportCsv() {
  const columns = visibleColumns.value.filter(column => column.key !== 'actions')

  const lines = [
    columns.map(column => `"${column.title.replace(/"/g, '""')}"`).join(','),
    ...filtered.value.map(item => columns.map(column => `"${cellText(item, column.key).replace(/"/g, '""')}"`).join(',')),
  ]

  const blob = new Blob([`\uFEFF${lines.join('\n')}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = url
  link.download = `${props.storageKey}.csv`
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div>
    <div class="d-flex flex-wrap justify-space-between align-center gap-4 mb-6">
      <div>
        <h4 class="text-h4">
          {{ title }}
        </h4>
        <p
          v-if="subtitle"
          class="text-body-1 text-medium-emphasis mb-0"
        >
          {{ subtitle }}
        </p>
      </div>
      <div class="d-flex flex-wrap gap-2">
        <VMenu>
          <template #activator="{ props: menu }">
            <VBtn
              v-bind="menu"
              variant="tonal"
              prepend-icon="tabler-columns"
            >
              {{ t('foundation.columns') }}
            </VBtn>
          </template>
          <VList>
            <VListItem
              v-for="column in columns"
              :key="column.key"
              @click="toggleColumn(column.key)"
            >
              <template #prepend>
                <VCheckbox
                  :model-value="!hidden.includes(column.key)"
                  density="compact"
                  hide-details
                />
              </template>
              <VListItemTitle>{{ column.title }}</VListItemTitle>
            </VListItem>
          </VList>
        </VMenu>
        <VMenu>
          <template #activator="{ props: menu }">
            <VBtn
              v-bind="menu"
              variant="tonal"
              prepend-icon="tabler-bookmark"
            >
              {{ t('foundation.savedViews') }}
            </VBtn>
          </template>
          <VList>
            <VListItem
              v-for="view in saved"
              :key="view.id"
            >
              <VListItemTitle @click="applyView(view)">
                {{ view.name }}
              </VListItemTitle>
              <template #append>
                <VBtn
                  icon="tabler-x"
                  size="x-small"
                  variant="text"
                  @click="removeView(view.id)"
                />
              </template>
            </VListItem>
            <VListItem @click="saveOpen = true">
              <VListItemTitle>{{ t('foundation.saveView') }}</VListItemTitle>
            </VListItem>
          </VList>
        </VMenu>
        <VBtn
          variant="tonal"
          prepend-icon="tabler-download"
          @click="exportCsv"
        >
          {{ t('foundation.exportCsv') }}
        </VBtn>
      </div>
    </div>

    <ErrorState
      v-if="error"
      :text="error"
      class="mb-4"
      @retry="emit('retry')"
    />

    <VCard>
      <VCardText class="d-flex flex-wrap gap-4">
        <AppTextField
          v-model="keyword"
          :label="t('foundation.keyword')"
          style="max-width: 240px;"
        />
        <AppSelect
          v-for="filter in filters"
          :key="filter.key"
          v-model="selects[filter.key]"
          :items="[{ title: t('common.allStores'), value: 'all' }, ...filter.items]"
          :label="filter.label"
          style="max-width: 220px;"
        />
        <AppTextField
          v-if="dateKey"
          v-model="dateFrom"
          type="date"
          :label="t('foundation.dateFrom')"
          style="max-width: 180px;"
        />
        <AppTextField
          v-if="dateKey"
          v-model="dateTo"
          type="date"
          :label="t('foundation.dateTo')"
          style="max-width: 180px;"
        />
      </VCardText>

      <div
        v-if="selectedRows.length"
        class="d-flex flex-wrap align-center gap-3 px-6 pb-2"
      >
        <span class="text-body-2">{{ t('foundation.selected') }} {{ selectedRows.length }}</span>
        <VBtn
          v-for="action in batchActions"
          :key="action.key"
          size="small"
          variant="tonal"
          @click="emit('batch', action.key, selectedRows)"
        >
          {{ action.label }}
        </VBtn>
        <slot
          name="batch"
          :selected="selectedRows"
        />
      </div>

      <LoadingState v-if="loading" />
      <EmptyState v-else-if="filtered.length === 0" />
      <VDataTable
        v-else
        v-model="selected"
        :headers="headers"
        :items="filtered"
        :items-per-page="10"
        show-select
        item-value="id"
      >
        <template
          v-for="column in visibleColumns"
          :key="column.key"
          #[`item.${column.key}`]="{ item }"
        >
          <slot
            :name="`item.${column.key}`"
            :item="item"
          >
            {{ cellText(item, column.key) }}
          </slot>
        </template>
      </VDataTable>
    </VCard>

    <VDialog
      v-model="saveOpen"
      max-width="420"
    >
      <VCard>
        <VCardItem>
          <VCardTitle>{{ t('foundation.saveView') }}</VCardTitle>
        </VCardItem>
        <VCardText>
          <AppTextField
            v-model="viewName"
            :label="t('foundation.viewName')"
          />
        </VCardText>
        <VCardActions>
          <VSpacer />
          <VBtn
            variant="text"
            @click="saveOpen = false"
          >
            {{ t('foundation.cancel') }}
          </VBtn>
          <VBtn
            color="primary"
            @click="saveView"
          >
            {{ t('foundation.save') }}
          </VBtn>
        </VCardActions>
      </VCard>
    </VDialog>
  </div>
</template>
