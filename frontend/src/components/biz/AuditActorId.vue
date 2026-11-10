<script setup lang="ts">
defineProps<{
  actorId: string
  inferred?: boolean
}>()
</script>

<template>
  <span>
    {{ actorId }}<VChip
      v-if="inferred"
      size="x-small"
      color="warning"
      class="ms-1"
    >推断</VChip>
  </span>
</template>
