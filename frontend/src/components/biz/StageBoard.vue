<script setup lang="ts">
/* eslint-disable max-statements-per-line */
interface Card { id: string; title: string; subtitle?: string; amount?: number; currency?: string; stage: string }
const props = defineProps<{ title: string; subtitle?: string; columns: { key: string; label: string; color: string }[]; cards: Card[] }>()
const emit = defineEmits<{ move: [card: Card, stage: string]; open: [card: Card] }>()
function drop(event: DragEvent, stage: string) {
  const id = event.dataTransfer?.getData('text/plain'); const card = props.cards.find(item => item.id === id); if (card)
    emit('move', card, stage)
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
    </div>
    <VRow>
      <VCol
        v-for="column in columns"
        :key="column.key"
        cols="12"
        md="3"
      >
        <VCard
          class="h-100"
          @dragover.prevent
          @drop="drop($event, column.key)"
        >
          <VCardItem>
            <VCardTitle class="d-flex align-center gap-2">
              <VBadge
                inline
                :color="column.color"
                dot
              />{{ column.label }}<VChip
                size="x-small"
                variant="tonal"
              >
                {{ cards.filter(card => card.stage === column.key).length }}
              </VChip>
            </VCardTitle>
          </VCardItem>
          <VCardText class="d-flex flex-column gap-3">
            <VCard
              v-for="card in cards.filter(item => item.stage === column.key)"
              :key="card.id"
              variant="outlined"
              draggable="true"
              @dragstart="(event: DragEvent) => event.dataTransfer?.setData('text/plain', card.id)"
              @click="emit('open', card)"
            >
              <VCardText>
                <div class="font-weight-medium">
                  {{ card.title }}
                </div><div class="text-caption text-medium-emphasis mt-1">
                  {{ card.subtitle }}
                </div><MoneyText
                  v-if="card.amount != null && card.currency"
                  class="d-block mt-3"
                  :amount="card.amount"
                  :currency="card.currency as never"
                />
              </VCardText>
            </VCard>
            <div
              v-if="!cards.some(item => item.stage === column.key)"
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
