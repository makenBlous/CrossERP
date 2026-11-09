<script setup lang="ts">
import GapBPage from '@/views/gap-b/GapBPage.vue'
const route = useRoute()
const isNew = computed(() => route.path !== '/admin/channels')
</script>

<template>
  <GapBPage :page-key="isNew ? 'SYS26' : 'SYS25'" />
</template>
