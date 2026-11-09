<script setup lang="ts">
import { fetchDictionaries } from '@/api/admin'
import ListPage from '@/components/biz/ListPage.vue'

const rows = ref<Array<{ id: string
  [key: string]: unknown }>>([])

onMounted(async () => {
  rows.value = await fetchDictionaries()
})

const columns = [{ key: 'group', title: '分组' }, { key: 'code', title: '编码' }, { key: 'label', title: '名称' }, { key: 'active', title: '启用' }]
</script>

<template>
  <ListPage
    storage-key="admin-dicts"
    title="数据字典"
    subtitle="原因码、工单状态和来源等可配置项。"
    :items="rows"
    :columns="columns"
  >
    <template #item.active="{ item }">
      <VChip
        size="small"
        :color="item.active ? 'success' : 'secondary'"
        variant="tonal"
      >
        {{ item.active ? '启用' : '停用' }}
      </VChip>
    </template>
  </ListPage>
</template>
