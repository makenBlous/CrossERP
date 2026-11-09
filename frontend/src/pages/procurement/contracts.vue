<script setup lang="ts">
import GapBPage from '@/views/gap-b/GapBPage.vue'
const route = useRoute()
const isDetail = computed(() => route.path !== '/procurement/contracts')
</script>

<template>
  <GapBPage :page-key="isDetail ? 'S12' : 'S11'" />
</template>
