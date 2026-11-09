<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchAdminUsers } from '@/api/admin'; import DetailPage from '@/components/biz/DetailPage.vue'

const route = useRoute(); const user = ref<Record<string, unknown> | null>(null)

onMounted(async () => { user.value = (await fetchAdminUsers()).find(item => item.id === String((route.params as Record<string, unknown>).id)) ?? null })
</script>

<template>
  <DetailPage
    v-if="user"
    :title="String(user.name)"
    :subtitle="String(user.email)"
  >
    <VCard title="账号信息">
      <VCardText>
        <VRow>
          <VCol
            cols="12"
            md="6"
          >
            <div class="text-caption">
              角色
            </div><VChip
              color="primary"
              variant="tonal"
            >
              {{ user.role }}
            </VChip>
          </VCol><VCol
            cols="12"
            md="6"
          >
            <div class="text-caption">
              店铺范围
            </div>{{ user.stores }}
          </VCol>
        </VRow>
      </VCardText>
    </VCard><VCard
      class="mt-6"
      title="登录安全"
    >
      <VCardText>
        <VAlert
          type="info"
          variant="tonal"
        >
          密码只在登录时校验，系统不会保存明文。
        </VAlert>
      </VCardText>
    </VCard>
  </DetailPage>
</template>
