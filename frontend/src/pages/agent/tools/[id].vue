<script setup lang="ts">
import BatchDPage from '@/views/gap-d/BatchDPage.vue'

const route = useRoute()
const pageId = computed(() => (route.params as Record<string, string | undefined>).id === 'new' ? 'G25' : 'G24')
</script>

<template>
  <BatchDPage :page-id="pageId" />
</template>
