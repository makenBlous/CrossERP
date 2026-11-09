<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchCrmLeads } from '@/api/crm'; import StageBoard from '@/components/biz/StageBoard.vue'; import { useMockDbStore } from '@/stores/mockdb'; import { useSessionStore } from '@/stores/session'; import type { Actor } from '@/types/entities'

const router = useRouter(); const store = useMockDbStore(); const session = useSessionStore(); const cards = ref<any[]>([]); const columns = [{ key: 'new', label: '新线索', color: 'secondary' }, { key: 'qualified', label: '已确认需求', color: 'info' }, { key: 'proposal', label: '已报价', color: 'warning' }, { key: 'converted', label: '已转化', color: 'success' }]
async function load() { cards.value = await fetchCrmLeads() }
onMounted(load)
function move(card: any, stage: string) { store.updateLeadStage(card.id, stage as never, { name: session.displayName, role: session.role, at: new Date().toISOString() } as Actor); card.stage = stage }
</script>

<template>
  <StageBoard
    title="线索看板"
    subtitle="拖动卡片推进阶段，变更会写入审计轨迹。"
    :columns="columns"
    :cards="cards.map(card => ({ ...card, title: card.name, subtitle: card.company, stage: card.stage }))"
    @move="move"
    @open="router.push(`/crm/leads/${$event.id}`)"
  />
</template>
