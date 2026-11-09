<script setup lang="ts">
import { sessionRoles, useSessionStore } from '@/stores/session'

const session = useSessionStore()
const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <VBtn
    variant="text"
    color="default"
    prepend-icon="tabler-user-shield"
  >
    {{ t(`role.${session.role}`) }}
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
          <VListItemTitle>{{ t(`role.${role}`) }}</VListItemTitle>
        </VListItem>
      </VList>
    </VMenu>
  </VBtn>
</template>
