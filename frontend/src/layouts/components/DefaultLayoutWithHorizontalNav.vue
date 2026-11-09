<script lang="ts" setup>
import Footer from '@/layouts/components/Footer.vue'
import NavbarThemeSwitcher from '@/layouts/components/NavbarThemeSwitcher.vue'
import RoleSwitcher from '@/layouts/components/RoleSwitcher.vue'
import UserProfile from '@/layouts/components/UserProfile.vue'
import { buildHorizontalNav } from '@/navigation/build-nav'
import { useSessionStore } from '@/stores/session'
import NavBarI18n from '@core/components/I18n.vue'
import { HorizontalNavLayout } from '@layouts'
import { VNodeRenderer } from '@layouts/components/VNodeRenderer'
import { themeConfig } from '@themeConfig'

const session = useSessionStore()
const navItems = computed(() => buildHorizontalNav(session.role))
</script>

<template>
  <HorizontalNavLayout :nav-items="navItems">
    <template #navbar>
      <RouterLink
        to="/dashboard"
        class="app-logo d-flex align-center gap-x-3"
      >
        <VNodeRenderer :nodes="themeConfig.app.logo" />
        <h1
          class="app-title font-weight-bold leading-normal text-xl"
          style="text-transform: none;"
        >
          CrossERP
        </h1>
      </RouterLink>
      <VSpacer />

      <RoleSwitcher />
      <NavBarI18n
        v-if="themeConfig.app.i18n.enable && themeConfig.app.i18n.langConfig?.length"
        :languages="themeConfig.app.i18n.langConfig"
      />
      <NavbarThemeSwitcher class="me-2" />
      <UserProfile />
    </template>

    <slot />

    <template #footer>
      <Footer />
    </template>
  </HorizontalNavLayout>
</template>
