<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchCrmOpportunities } from '@/api/crm'; import StageBoard from '@/components/biz/StageBoard.vue'

const router = useRouter(); const cards = ref<any[]>([]); const columns = [{ key: '初步沟通', label: '初步沟通', color: 'secondary' }, { key: '报价', label: '报价', color: 'info' }, { key: '谈判', label: '谈判', color: 'warning' }, { key: '赢单', label: '赢单', color: 'success' }]

onMounted(async () => { cards.value = await fetchCrmOpportunities() })
</script>

<template>
  <StageBoard
    title="商机看板"
    subtitle="按销售阶段查看预计金额。金额由系统存储并格式化。"
    :columns="columns"
    :cards="cards.map(card => ({ ...card, title: card.name, subtitle: card.accountName, stage: card.stage }))"
    @open="router.push(`/crm/opportunities/${$event.id}`)"
  />
</template>
