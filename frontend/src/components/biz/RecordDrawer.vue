<script setup lang="ts">
import { PerfectScrollbar } from 'vue3-perfect-scrollbar'

withDefaults(defineProps<{
  modelValue: boolean
  title: string
  width?: number
}>(), {
  width: 440,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>

<template>
  <!-- 只读抽屉外壳，同审批页：AppDrawerHeaderSection + PerfectScrollbar。 -->
  <VNavigationDrawer
    :model-value="modelValue"
    data-allow-mismatch
    temporary
    location="end"
    :width="width"
    class="scrollable-content"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <AppDrawerHeaderSection
      :title="title"
      @cancel="emit('update:modelValue', false)"
    />
    <VDivider />
    <PerfectScrollbar :options="{ wheelPropagation: false }">
      <VCard flat>
        <VCardText>
          <slot />
        </VCardText>
      </VCard>
    </PerfectScrollbar>
  </VNavigationDrawer>
</template>
