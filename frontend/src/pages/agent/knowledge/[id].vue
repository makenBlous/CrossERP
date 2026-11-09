<script setup lang="ts">
const router = useRouter()
const route = useRoute()

onMounted(() => router.replace(`/kb/spaces/${String((route.params as Record<string, unknown>).id)}`))
</script>

<template>
  <VProgressCircular
    indeterminate
    color="primary"
  />
</template>
