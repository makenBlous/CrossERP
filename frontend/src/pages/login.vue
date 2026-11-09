<script setup lang="ts">
import { useGenerateImageVariant } from '@core/composable/useGenerateImageVariant'
import authV2LoginIllustrationBorderedDark from '@images/pages/auth-v2-login-illustration-bordered-dark.png'
import authV2LoginIllustrationBorderedLight from '@images/pages/auth-v2-login-illustration-bordered-light.png'
import authV2LoginIllustrationDark from '@images/pages/auth-v2-login-illustration-dark.png'
import authV2LoginIllustrationLight from '@images/pages/auth-v2-login-illustration-light.png'
import authV2MaskDark from '@images/pages/misc-mask-dark.png'
import authV2MaskLight from '@images/pages/misc-mask-light.png'
import NavBarI18n from '@core/components/I18n.vue'
import { VNodeRenderer } from '@layouts/components/VNodeRenderer'
import { themeConfig } from '@themeConfig'
import NavbarThemeSwitcher from '@/layouts/components/NavbarThemeSwitcher.vue'
import { useSessionStore } from '@/stores/session'

definePage({
  meta: {
    layout: 'blank',
    public: true,
    unauthenticatedOnly: true,
  },
})

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const { t } = useI18n({ useScope: 'global' })

const form = ref({
  username: '',
  remember: false,
})

const isPasswordVisible = ref(false)
const password = ref('')

const authThemeImg = useGenerateImageVariant(
  authV2LoginIllustrationLight,
  authV2LoginIllustrationDark,
  authV2LoginIllustrationBorderedLight,
  authV2LoginIllustrationBorderedDark,
  true,
)

const authThemeMask = useGenerateImageVariant(authV2MaskLight, authV2MaskDark)

function submit() {
  session.login(form.value.username)
  password.value = ''

  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'

  router.push(redirect)
}
</script>

<template>
  <div class="auth-logo d-flex align-center gap-x-3">
    <VNodeRenderer :nodes="themeConfig.app.logo" />
    <h1
      class="auth-title"
      style="text-transform: none;"
    >
      CrossERP
    </h1>
    <VSpacer />
    <NavbarThemeSwitcher />
    <NavBarI18n
      v-if="themeConfig.app.i18n.langConfig?.length"
      :languages="themeConfig.app.i18n.langConfig"
    />
  </div>

  <VRow
    no-gutters
    class="auth-wrapper bg-surface"
  >
    <VCol
      md="8"
      class="d-none d-md-flex"
    >
      <div class="position-relative bg-background w-100 me-0">
        <div
          class="d-flex align-center justify-center w-100 h-100"
          style="padding-inline: 6.25rem;"
        >
          <VImg
            max-width="613"
            :src="authThemeImg"
            class="auth-illustration mt-16 mb-2"
          />
        </div>

        <img
          class="auth-footer-mask flip-in-rtl"
          :src="authThemeMask"
          alt=""
          height="280"
          width="100"
        >
      </div>
    </VCol>

    <VCol
      cols="12"
      md="4"
      class="auth-card-v2 d-flex align-center justify-center"
    >
      <VCard
        flat
        :max-width="500"
        class="mt-12 mt-sm-0 pa-6"
      >
        <VCardText>
          <h4 class="text-h4 mb-1">
            {{ t('login.welcome') }}
          </h4>
          <p class="mb-0">
            {{ t('login.subtitle') }}
          </p>
        </VCardText>
        <VCardText>
          <VAlert
            type="info"
            variant="tonal"
            class="mb-4"
          >
            {{ t('login.hint') }}
          </VAlert>
          <VForm @submit.prevent="submit">
            <VRow>
              <VCol cols="12">
                <AppTextField
                  v-model="form.username"
                  autofocus
                  :label="t('login.username')"
                  placeholder="linxia"
                />
              </VCol>
              <VCol cols="12">
                <AppTextField
                  v-model="password"
                  :label="t('login.password')"
                  placeholder="············"
                  :type="isPasswordVisible ? 'text' : 'password'"
                  autocomplete="current-password"
                  :append-inner-icon="isPasswordVisible ? 'tabler-eye-off' : 'tabler-eye'"
                  @click:append-inner="isPasswordVisible = !isPasswordVisible"
                />
                <div class="d-flex align-center flex-wrap justify-space-between my-6">
                  <VCheckbox
                    v-model="form.remember"
                    :label="t('login.remember')"
                  />
                  <RouterLink
                    class="text-primary"
                    to="/forgot-password"
                  >
                    {{ t('login.forgot') }}
                  </RouterLink>
                </div>
                <VBtn
                  block
                  type="submit"
                >
                  {{ t('login.submit') }}
                </VBtn>
              </VCol>
            </VRow>
          </VForm>
        </VCardText>
      </VCard>
    </VCol>
  </VRow>
</template>

<style lang="scss">
@use "@core/scss/template/pages/page-auth";
</style>
