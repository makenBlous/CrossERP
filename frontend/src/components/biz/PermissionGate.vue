<script setup lang="ts">
import { useSessionStore } from '@/stores/session'
import { usePermissionStore } from '@/stores/permissions'
import type { AppAction } from '@/utils/permission'
import { can } from '@/utils/permission'
import { roleSubject } from '@/utils/permission-engine'

const props = defineProps<{
  action?: AppAction
  permission?: string
}>()

const session = useSessionStore()
const permissions = usePermissionStore()
const allowed = computed(() => {
  if (props.permission)
    return permissions.effective(roleSubject(session.role, session.userId)).some(item => item.permissionKey === props.permission && item.allowed)

  return props.action ? can(session.role, props.action) : false
})
</script>

<template>
  <!-- Vuexy 的 CASL 插件管的是模板演示权限，不是本项目的五种角色。显隐仍走 can(role, action)。 -->
  <slot v-if="allowed" />
</template>
