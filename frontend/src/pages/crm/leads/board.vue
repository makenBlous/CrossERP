<script setup lang="ts">
import { fetchCrmLeads, updateCrmLeadStage } from '@/api/crm'
import CrmKanbanBoard from '@/views/crm/kanban/CrmKanbanBoard.vue'

const router = useRouter()
const cards = ref<any[]>([])
const columns = [{ key: 'new', label: '新线索', color: 'secondary' }, { key: 'qualified', label: '已确认需求', color: 'info' }, { key: 'proposal', label: '已报价', color: 'warning' }, { key: 'converted', label: '已转化', color: 'success' }]
async function load() {
  cards.value = await fetchCrmLeads()
}
onMounted(load)
async function move(card: any, stage: string) {
  await updateCrmLeadStage(card.id, stage as never)
  card.stage = stage
}
</script>

<template>
  <CrmKanbanBoard
    title="线索看板"
    subtitle="拖动卡片推进阶段，变更会写入审计轨迹。"
    :columns="columns"
    :cards="cards.map(card => ({ ...card, title: card.name, subtitle: card.company, stage: card.stage }))"
    @move="move"
    @open="router.push(`/crm/leads/${$event.id}`)"
  />
</template>
