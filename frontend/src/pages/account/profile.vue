<script setup lang="ts">
import { fetchProfile } from '@/api/account'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const profile = ref<Record<string, string>>({})

onMounted(async () => {
  profile.value = await fetchProfile()
})
function save() {
  if (profile.value.name.trim()) {
    session.displayName = profile.value.name
    session.login(profile.value.name)
  }
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        我的资料
      </h4><p class="text-body-1 mb-0">
        更新显示名和工作信息。
      </p>
    </div><VCard max-width="760">
      <VCardText>
        <VRow>
          <VCol
            cols="12"
            md="6"
          >
            <AppTextField
              v-model="profile.name"
              label="显示名"
            />
          </VCol><VCol
            cols="12"
            md="6"
          >
            <AppTextField
              v-model="profile.email"
              label="邮箱"
              readonly
            />
          </VCol><VCol
            cols="12"
            md="6"
          >
            <AppTextField
              v-model="profile.title"
              label="职位"
            />
          </VCol><VCol
            cols="12"
            md="6"
          >
            <AppTextField
              v-model="profile.timezone"
              label="时区"
            />
          </VCol>
        </VRow>
      </VCardText><VCardActions>
        <VSpacer /><VBtn
          color="primary"
          @click="save"
        >
          保存资料
        </VBtn>
      </VCardActions>
    </VCard>
  </div>
</template>
