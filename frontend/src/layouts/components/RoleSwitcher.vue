<script setup lang="ts">
import { sessionRoles, useSessionStore } from '@/stores/session'
import { roleTemplates } from '@/config/permissions'

const session = useSessionStore()
const { t } = useI18n({ useScope: 'global' })
const templateLabels = new Map(roleTemplates.map(item => [item.id, item.nameZh]))

function roleLabel(role: string) {
  return templateLabels.get(role) ?? t(`role.${role}`)
}
</script>

<template>
  <VBtn
    variant="text"
    color="default"
    prepend-icon="tabler-user-shield"
  >
    {{ roleLabel(session.role) }}
    <VMenu
      activator="parent"
      location="bottom end"
      offset="12px"
    >
      <VList
        :selected="[session.role]"
        color="primary"
        min-width="160"
      >
        <VListItem
          v-for="role in sessionRoles"
          :key="role"
          :value="role"
          @click="session.setRole(role)"
        >
          <VListItemTitle>{{ roleLabel(role) }}</VListItemTitle>
        </VListItem>
      </VList>
    </VMenu>
  </VBtn>
</template>
