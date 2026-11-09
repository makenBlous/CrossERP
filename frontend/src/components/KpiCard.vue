<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  value: string
  icon: string
  color?: string
  hint?: string
}>(), {
  color: 'primary',
})
</script>

<template>
  <!-- 统计区用 Vuexy CardStatisticsHorizontal。该组件没有 hint，所以只在下方补一行说明。 -->
  <div>
    <CardStatisticsHorizontal
      :title="title"
      :stats="value"
      :icon="icon"
      :color="color"
    />
    <div
      v-if="hint"
      class="text-caption text-medium-emphasis px-1 mt-1"
    >
      {{ hint }}
    </div>
  </div>
</template>
