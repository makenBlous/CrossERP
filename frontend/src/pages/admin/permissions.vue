<script setup lang="ts">
import { fetchPermissions } from '@/api/admin'
import ListPage from '@/components/biz/ListPage.vue'

const rows = ref<Array<{ id: string
  [key: string]: unknown }>>([])

onMounted(async () => {
  rows.value = await fetchPermissions()
})

const columns = [{ key: 'code', title: '权限编码' }, { key: 'name', title: '名称' }, { key: 'id', title: '标识' }]
</script>

<template>
  <ListPage
    storage-key="admin-permissions"
    title="权限点"
    subtitle="系统动作权限目录。"
    :items="rows"
    :columns="columns"
  />
</template>
