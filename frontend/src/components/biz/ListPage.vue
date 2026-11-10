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

  /** 为 true 时「全部」写成「全部店铺」。默认只认 store / storeId / storeName。 */
  store?: boolean
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
  embedded?: boolean
}>(), {
  subtitle: '',
  filters: () => [],
  dateKey: '',
  loading: false,
  error: '',
  batchActions: () => [],
  embedded: false,
})

const emit = defineEmits<{
  retry: []
  batch: [action: string, rows: T[]]
  open: [row: T]
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
const page = ref(1)
const itemsPerPage = ref(10)
const dateConfig = { dateFormat: 'Y-m-d', allowInput: true }
const pageSizes = [10, 25, 50, 100]
const storeKeys = new Set(['store', 'storeId', 'storeName'])

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

function allTitle(filter: ListSelectFilter) {
  if (filter.store || storeKeys.has(filter.key))
    return t('common.allStores')

  return t('common.all')
}

const filtered = computed(() => props.items.filter(item => {
  const text = props.columns.map(column => cellText(item, column.key)).join(' ').toLowerCase()
  const keywordOk = text.includes(keyword.value.trim().toLowerCase())

  const selectOk = (props.filters ?? []).every(filter => {
    const chosen = selects[filter.key] || 'all'

    return chosen === 'all' || cellText(item, filter.key) === chosen
  })

  const date = rowDate(item)
  const fromOk = !dateFrom.value || !date || date >= dateFrom.value.slice(0, 10)
  const toOk = !dateTo.value || !date || date <= dateTo.value.slice(0, 10)

  return keywordOk && selectOk && fromOk && toOk
}))

const paged = computed(() => {
  const start = (page.value - 1) * itemsPerPage.value

  return filtered.value.slice(start, start + itemsPerPage.value)
})

watch([keyword, dateFrom, dateTo, itemsPerPage], () => {
  page.value = 1
})

watch(selects, () => {
  page.value = 1
}, { deep: true })

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

function onRowClick(event: Event, payload: { item: T & { raw?: T } }) {
  const target = event.target

  if (target instanceof Element && target.closest('button, a, input, .v-selection-control'))
    return

  const item = payload.item.raw ?? payload.item

  if (item?.id)
    emit('open', item)
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

function setPageSize(value: unknown) {
  const next = Number(value)

  if (Number.isFinite(next) && next > 0)
    itemsPerPage.value = next
}
</script>

<template>
  <!-- 薄封装：结构来自 Vuexy ecommerce product list / user list / invoice list。顶部统计走 #widgets。 -->
  <div>
    <div
      v-if="!embedded"
      class="d-flex flex-wrap justify-space-between align-center gap-4 mb-6"
    >
      <div>
        <h4 class="text-h4">
          {{ title }}
        </h4>
        <p
          v-if="subtitle"
          class="text-body-1 mb-0"
        >
          {{ subtitle }}
        </p>
      </div>
      <div
        v-if="$slots.actions"
        class="d-flex align-center gap-3 flex-wrap"
      >
        <slot name="actions" />
      </div>
    </div>

    <slot name="widgets" />

    <ErrorState
      v-if="error"
      :text="error"
      class="mb-4"
      @retry="emit('retry')"
    />

    <VCard>
      <template v-if="(filters?.length ?? 0) > 0 || dateKey">
        <VCardItem class="pb-4">
          <VCardTitle>{{ t('foundation.filters') }}</VCardTitle>
        </VCardItem>
        <VCardText>
          <VRow>
            <VCol
              v-for="filter in filters"
              :key="filter.key"
              cols="12"
              sm="4"
            >
              <AppSelect
                v-model="selects[filter.key]"
                :items="[{ title: allTitle(filter), value: 'all' }, ...filter.items]"
                :label="filter.label"
                :placeholder="filter.label"
              />
            </VCol>
            <VCol
              v-if="dateKey"
              cols="12"
              sm="4"
            >
              <AppDateTimePicker
                v-model="dateFrom"
                :label="t('foundation.dateFrom')"
                :placeholder="t('foundation.dateFrom')"
                :config="dateConfig"
                clearable
              />
            </VCol>
            <VCol
              v-if="dateKey"
              cols="12"
              sm="4"
            >
              <AppDateTimePicker
                v-model="dateTo"
                :label="t('foundation.dateTo')"
                :placeholder="t('foundation.dateTo')"
                :config="dateConfig"
                clearable
              />
            </VCol>
          </VRow>
        </VCardText>
        <VDivider />
      </template>

      <div class="d-flex flex-wrap gap-4 ma-6">
        <AppTextField
          v-model="keyword"
          :placeholder="t('foundation.keyword')"
          style="inline-size: 15rem;"
        />
        <VSpacer />
        <div class="d-flex gap-4 flex-wrap align-center">
          <AppSelect
            :model-value="itemsPerPage"
            :items="pageSizes"
            :label="t('foundation.perPage')"
            style="inline-size: 8rem;"
            @update:model-value="setPageSize"
          />
          <VMenu>
            <template #activator="{ props: menu }">
              <VBtn
                v-bind="menu"
                variant="tonal"
                color="secondary"
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
                color="secondary"
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
                  <IconBtn
                    size="small"
                    @click="removeView(view.id)"
                  >
                    <VIcon icon="tabler-x" />
                  </IconBtn>
                </template>
              </VListItem>
              <VListItem @click="saveOpen = true">
                <VListItemTitle>{{ t('foundation.saveView') }}</VListItemTitle>
              </VListItem>
            </VList>
          </VMenu>
          <VBtn
            variant="tonal"
            color="secondary"
            prepend-icon="tabler-upload"
            @click="exportCsv"
          >
            {{ t('foundation.exportCsv') }}
          </VBtn>
        </div>
      </div>

      <VDivider />

      <div
        v-if="selectedRows.length"
        class="d-flex flex-wrap align-center gap-3 px-6 py-3"
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

      <VSkeletonLoader
        v-if="loading"
        type="table-heading, table-thead, table-row@6"
      />
      <VDataTableServer
        v-else
        v-model:model-value="selected"
        v-model:items-per-page="itemsPerPage"
        v-model:page="page"
        :headers="headers"
        :items="paged"
        :items-length="filtered.length"
        show-select
        item-value="id"
        class="text-no-wrap"
        @click:row="onRowClick"
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
        <template #no-data>
          <EmptyState />
        </template>
        <template #bottom>
          <TablePagination
            v-model:page="page"
            :items-per-page="itemsPerPage"
            :total-items="filtered.length"
          />
        </template>
      </VDataTableServer>
    </VCard>

    <VDialog
      v-model="saveOpen"
      max-width="420"
    >
      <DialogCloseBtn @click="saveOpen = false" />
      <VCard :title="t('foundation.saveView')">
        <VCardText>
          <AppTextField
            v-model="viewName"
            :label="t('foundation.viewName')"
            :rules="[requiredValidator]"
          />
        </VCardText>
        <VCardText class="d-flex justify-end gap-3">
          <VBtn
            variant="tonal"
            color="secondary"
            @click="saveOpen = false"
          >
            {{ t('foundation.cancel') }}
          </VBtn>
          <VBtn @click="saveView">
            {{ t('foundation.save') }}
          </VBtn>
        </VCardText>
      </VCard>
    </VDialog>
  </div>
</template>
