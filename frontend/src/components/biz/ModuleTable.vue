<script setup lang="ts">
import ListPage from '@/components/biz/ListPage.vue'

interface Row { id: string; [key: string]: unknown }
const props = withDefaults(defineProps<{ title: string; subtitle?: string; rows: Row[]; columns: { key: string; title: string; align?: 'start' | 'end' | 'center' }[]; storageKey: string; filters?: { key: string; label: string; items: { title: string; value: string }[] }[] }>(), { subtitle: '', filters: () => [] })
const emit = defineEmits<{ open: [row: Row] }>()
</script>

<template>
  <ListPage
    :storage-key="props.storageKey"
    :title="props.title"
    :subtitle="props.subtitle"
    :items="props.rows"
    :columns="props.columns"
    :filters="props.filters"
    @open="emit('open', $event)"
  >
    <template
      v-for="column in props.columns"
      #[`item.${column.key}`]="{ item }"
      :key="column.key"
    >
      <slot
        :name="`cell.${column.key}`"
        :item="item"
      >
        {{ item[column.key] }}
      </slot>
    </template>
    <template #widgets>
      <slot name="widgets" />
    </template>
  </ListPage>
</template>
