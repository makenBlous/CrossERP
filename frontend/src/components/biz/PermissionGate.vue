<script setup lang="ts">
import { useSessionStore } from '@/stores/session'
import type { AppAction } from '@/utils/permission'
import { can } from '@/utils/permission'

const props = defineProps<{
  action: AppAction
}>()

const session = useSessionStore()
const allowed = computed(() => can(session.role, props.action))
</script>

<template>
  <slot v-if="allowed" />
</template>
