<script setup lang="ts">
interface Props {
  title: string
  value: string
  icon: string
  color?: string
  hint?: string
}

withDefaults(defineProps<Props>(), {
  color: 'primary',
})
</script>

<template>
  <VCard>
    <VCardText class="d-flex justify-space-between align-start">
      <div>
        <div class="text-body-2 text-medium-emphasis">
          {{ title }}
        </div>
        <div class="text-h5 mt-1">
          {{ value }}
        </div>
        <div
          v-if="hint"
          class="text-caption text-medium-emphasis mt-1"
        >
          {{ hint }}
        </div>
      </div>
      <VAvatar
        :color="color"
        variant="tonal"
        rounded
        size="42"
      >
        <VIcon
          :icon="icon"
          size="24"
        />
      </VAvatar>
    </VCardText>
  </VCard>
</template>
