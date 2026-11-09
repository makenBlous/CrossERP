<script setup lang="ts">
import ListPage from '@/components/biz/ListPage.vue'

export interface FinanceRow { id: string; [key: string]: unknown }
export interface FinanceColumn { key: string; title: string; align?: 'start' | 'end' | 'center' }

const props = withDefaults(defineProps<{
  storageKey: string
  title: string
  subtitle?: string
  rows: FinanceRow[]
  columns: FinanceColumn[]
  detailBase?: string
  notice?: string
}>(), { subtitle: '', detailBase: '', notice: '' })

const router = useRouter()

function open(row: FinanceRow) {
  if (props.detailBase)
    router.push(`${props.detailBase}/${row.id}`)
}
</script>

<template>
  <div>
    <VAlert
      v-if="notice"
      type="info"
      variant="tonal"
      class="mb-6"
    >
      {{ notice }}
    </VAlert>
    <ListPage
      :storage-key="storageKey"
      :title="title"
      :subtitle="subtitle"
      :items="rows"
      :columns="columns"
      @open="open"
    >
      <template
        v-for="column in columns"
        #[`item.${column.key}`]="{ item }"
        :key="column.key"
      >
        <slot
          :name="`item.${column.key}`"
          :item="item"
        >
          {{ item[column.key] ?? '—' }}
        </slot>
      </template>
    </ListPage>
  </div>
</template>
