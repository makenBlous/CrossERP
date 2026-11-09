<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchStores } from '@/api/dashboard'; import ModuleTable from '@/components/biz/ModuleTable.vue'

const rows = ref<Array<{ id: string; [key: string]: unknown }>>([])

onMounted(async () => { rows.value = (await fetchStores()).map(item => ({ ...item })) as Array<{ id: string; [key: string]: unknown }> })

const columns = [{ key: 'name', title: '店铺' }, { key: 'platform', title: '平台' }, { key: 'marketplace', title: '站点' }, { key: 'currency', title: '币种' }]
</script>

<template>
  <ModuleTable
    storage-key="admin-stores"
    title="店铺"
    subtitle="维护 Amazon、Shopify 和 TikTok Shop 店铺。"
    :rows="rows"
    :columns="columns"
  />
</template>
