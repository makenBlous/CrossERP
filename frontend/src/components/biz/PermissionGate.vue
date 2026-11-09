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
  <!-- Vuexy 的 CASL 插件管的是模板演示权限，不是本项目的五种角色。显隐仍走 can(role, action)。 -->
  <slot v-if="allowed" />
</template>
