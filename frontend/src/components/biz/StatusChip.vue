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
  <!-- Vuexy 的 VChip 没有业务状态字典。颜色和中英文名来自 src/config/status.ts，这里只做薄封装。 -->
  <VChip
    :color="found.color"
    size="small"
    label
  >
    {{ label }}
  </VChip>
</template>
