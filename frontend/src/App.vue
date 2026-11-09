<script setup lang="ts">
import { useTheme } from 'vuetify'
import ScrollToTop from '@core/components/ScrollToTop.vue'
import AssistantDrawer from '@/components/biz/AssistantDrawer.vue'
import ConfirmHost from '@/components/biz/ConfirmHost.vue'
import { useAiModeStore } from '@/stores/ai-mode'
import initCore from '@core/initCore'
import { initConfigStore, useConfigStore } from '@core/stores/config'
import { hexToRgb } from '@core/utils/colorConverter'

const { global } = useTheme()

// ℹ️ Sync current theme with initial loader theme
initCore()
initConfigStore()

const configStore = useConfigStore()
const aiMode = useAiModeStore()
</script>

<template>
  <VLocaleProvider :rtl="configStore.isAppRTL">
    <!-- ℹ️ This is required to set the background color of active nav link based on currently active global theme's primary -->
    <VApp :style="`--v-global-theme-primary: ${hexToRgb(global.current.value.colors.primary)}`">
      <RouterView />

      <AssistantDrawer v-if="aiMode.isEnabled" />
      <ConfirmHost />
      <ScrollToTop />
    </VApp>
  </VLocaleProvider>
</template>
