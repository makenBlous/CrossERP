<script lang="ts" setup>
import Footer from '@/layouts/components/Footer.vue'
import NavbarThemeSwitcher from '@/layouts/components/NavbarThemeSwitcher.vue'
import RoleSwitcher from '@/layouts/components/RoleSwitcher.vue'
import UserProfile from '@/layouts/components/UserProfile.vue'
import { buildNav } from '@/navigation/build-nav'
import { useSessionStore } from '@/stores/session'
import NavBarI18n from '@core/components/I18n.vue'
import { VerticalNavLayout } from '@layouts'
import { themeConfig } from '@themeConfig'

const session = useSessionStore()
const { t } = useI18n({ useScope: 'global' })
const navItems = computed(() => buildNav(session.role))
</script>

<template>
  <VerticalNavLayout :nav-items="navItems">
    <template #navbar="{ toggleVerticalOverlayNavActive }">
      <div class="d-flex h-100 align-center">
        <IconBtn
          id="vertical-nav-toggle-btn"
          class="ms-n3 d-lg-none"
          @click="toggleVerticalOverlayNavActive(true)"
        >
          <VIcon
            size="26"
            icon="tabler-menu-2"
          />
        </IconBtn>

        <NavbarThemeSwitcher />
        <VChip
          size="small"
          color="primary"
          variant="tonal"
          class="ms-2 d-none d-sm-flex"
        >
          {{ t('common.prototype') }}
        </VChip>

        <VSpacer />

        <RoleSwitcher />
        <NavBarI18n
          v-if="themeConfig.app.i18n.enable && themeConfig.app.i18n.langConfig?.length"
          :languages="themeConfig.app.i18n.langConfig"
        />
        <UserProfile />
      </div>
    </template>

    <slot />

    <template #footer>
      <Footer />
    </template>
  </VerticalNavLayout>
</template>
