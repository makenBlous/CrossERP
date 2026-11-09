<script setup lang="ts">
import GapBPage from '@/views/gap-b/GapBPage.vue'
const route = useRoute()
const isDetail = computed(() => route.path !== '/procurement/rfqs')
</script>

<template>
  <GapBPage :page-key="isDetail ? 'S10' : 'S09'" />
</template>
