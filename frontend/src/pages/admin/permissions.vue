<script setup lang="ts">
import { fetchPermissions } from '@/api/admin'
import ModuleTable from '@/components/biz/ModuleTable.vue'

const rows = ref<Array<{ id: string
  [key: string]: unknown }>>([])

onMounted(async () => {
  rows.value = await fetchPermissions()
})

const columns = [{ key: 'code', title: '权限编码' }, { key: 'name', title: '名称' }, { key: 'id', title: '标识' }]
</script>

<template>
  <ModuleTable
    storage-key="admin-permissions"
    title="权限点"
    subtitle="系统动作权限目录。"
    :rows="rows"
    :columns="columns"
  />
</template>
