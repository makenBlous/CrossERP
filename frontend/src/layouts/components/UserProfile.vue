<script setup lang="ts">
import avatar1 from '@images/avatars/avatar-1.png'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const router = useRouter()
const { t } = useI18n({ useScope: 'global' })

function logout() {
  session.logout()
  router.push('/login')
}
</script>

<template>
  <VBadge
    dot
    location="bottom right"
    offset-x="3"
    offset-y="3"
    bordered
    color="success"
  >
    <VAvatar
      class="cursor-pointer"
      color="primary"
      variant="tonal"
    >
      <VImg :src="avatar1" />

      <VMenu
        activator="parent"
        width="240"
        location="bottom end"
        offset="14px"
      >
        <VList>
          <VListItem>
            <VListItemTitle class="font-weight-semibold">
              {{ session.displayName }}
            </VListItemTitle>
            <VListItemSubtitle>{{ t(`role.${session.role}`) }}</VListItemSubtitle>
          </VListItem>

          <VDivider class="my-2" />

          <VListItem to="/account/profile">
            <template #prepend>
              <VIcon
                class="me-2"
                icon="tabler-user"
                size="22"
              />
            </template>
            <VListItemTitle>{{ t('common.profile') }}</VListItemTitle>
          </VListItem>

          <VListItem to="/account/tokens">
            <template #prepend>
              <VIcon
                class="me-2"
                icon="tabler-key"
                size="22"
              />
            </template>
            <VListItemTitle>{{ t('common.tokens') }}</VListItemTitle>
          </VListItem>

          <VListItem to="/account/sessions">
            <template #prepend>
              <VIcon
                class="me-2"
                icon="tabler-devices"
                size="22"
              />
            </template>
            <VListItemTitle>{{ t('common.sessions') }}</VListItemTitle>
          </VListItem>

          <VDivider class="my-2" />

          <VListItem @click="logout">
            <template #prepend>
              <VIcon
                class="me-2"
                icon="tabler-logout"
                size="22"
              />
            </template>
            <VListItemTitle>{{ t('common.logout') }}</VListItemTitle>
          </VListItem>
        </VList>
      </VMenu>
    </VAvatar>
  </VBadge>
</template>
