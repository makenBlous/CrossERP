<script setup lang="ts">
import KnowledgePage from '@/views/knowledge/KnowledgePage.vue'

const route = useRoute()
const isEdit = computed(() => route.path.endsWith('/edit'))
</script>

<template>
  <KnowledgePage :mode="isEdit ? 'edit' : 'doc'" />
</template>
