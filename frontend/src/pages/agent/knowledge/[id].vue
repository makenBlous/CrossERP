<script setup lang="ts">
const router = useRouter()
const route = useRoute()

onMounted(() => {
  const legacyId = String((route.params as Record<string, unknown>).id)

  // The old demo knowledge base was folded into the company space in batch E.
  // Keep the legacy route accessible to its original roles while avoiding a
  // redirect to the removed kb-rules space.
  router.replace(`/kb/spaces/${legacyId === 'kb-rules' ? 'space-company' : legacyId}`)
})
</script>

<template>
  <VProgressCircular
    indeterminate
    color="primary"
  />
</template>
