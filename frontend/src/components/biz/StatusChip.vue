<script setup lang="ts">
import { type StatusDomain, findStatus } from '@/config/status'

const props = defineProps<{
  domain: StatusDomain
  value: string
}>()

const { locale } = useI18n({ useScope: 'global' })
const found = computed(() => findStatus(props.domain, props.value))
const label = computed(() => String(locale.value).startsWith('en') ? found.value.en : found.value.zh)
</script>

<template>
  <VChip
    :color="found.color"
    size="small"
    label
  >
    {{ label }}
  </VChip>
</template>
