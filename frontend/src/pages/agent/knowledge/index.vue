<script setup lang="ts">
const router = useRouter()

onMounted(() => router.replace('/kb'))
</script>

<template>
  <VProgressCircular
    indeterminate
    color="primary"
  />
</template>
