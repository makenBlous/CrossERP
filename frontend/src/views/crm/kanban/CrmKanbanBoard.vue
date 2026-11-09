<script setup lang="ts">
import { useDragAndDrop } from '@formkit/drag-and-drop/vue'
import MoneyText from '@/components/biz/MoneyText.vue'

interface Card { id: string; title: string; subtitle?: string; amount?: number; currency?: string; stage: string }
const props = defineProps<{ title: string; subtitle?: string; columns: { key: string; label: string; color: string }[]; cards: Card[] }>()
const emit = defineEmits<{ move: [card: Card, stage: string]; open: [card: Card] }>()

const boards = props.columns.map(column => {
  const [parent, values] = useDragAndDrop<string>([], { group: 'crosserp-crm', name: column.key, sortable: true })

  return { column, parent, values }
})

const ready = ref(false)
const cardMap = computed(() => new Map(props.cards.map(card => [card.id, card])))

watch(() => props.cards, cards => {
  for (const board of boards)
    board.values.value = cards.filter(card => card.stage === board.column.key).map(card => card.id)
}, { immediate: true, deep: true })
onMounted(() => {
  ready.value = true
})
for (const board of boards) {
  watch(board.values, values => {
    if (!ready.value)
      return
    for (const id of values) {
      const card = cardMap.value.get(id)
      if (card && card.stage !== board.column.key)
        emit('move', card, board.column.key)
    }
  }, { deep: true })
}
function boardIds(board: (typeof boards)[number]) {
  return board.values.value
}
</script>

<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h4 class="text-h4">
          {{ title }}
        </h4><p class="text-body-1 mb-0">
          {{ subtitle }}
        </p>
      </div>
    </div><VRow>
      <VCol
        v-for="board in boards"
        :key="board.column.key"
        cols="12"
        md="3"
      >
        <VCard class="h-100">
          <VCardItem>
            <VCardTitle class="d-flex align-center gap-2">
              <VBadge
                inline
                :color="board.column.color"
                dot
              />{{ board.column.label }}<VChip
                size="x-small"
                variant="tonal"
              >
                {{ boardIds(board).length }}
              </VChip>
            </VCardTitle>
          </VCardItem><VCardText
            :ref="board.parent"
            class="d-flex flex-column gap-3 min-h-100"
          >
            <VCard
              v-for="cardId in boardIds(board)"
              :key="cardId"
              class="kanban-card"
              variant="outlined"
              draggable="true"
              @click="cardMap.get(cardId) && emit('open', cardMap.get(cardId)!)"
            >
              <VCardText>
                <div class="font-weight-medium">
                  {{ cardMap.get(cardId)?.title }}
                </div><div class="text-caption text-medium-emphasis mt-1">
                  {{ cardMap.get(cardId)?.subtitle }}
                </div><MoneyText
                  v-if="cardMap.get(cardId)?.amount != null && cardMap.get(cardId)?.currency"
                  class="d-block mt-3"
                  :amount="cardMap.get(cardId)!.amount!"
                  :currency="cardMap.get(cardId)!.currency as never"
                />
              </VCardText>
            </VCard><div
              v-if="!boardIds(board).length"
              class="text-caption text-disabled text-center py-6"
            >
              拖拽卡片到这里
            </div>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>
