<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchIntegrations } from '@/api/admin'

const rows = ref<any[]>([])

onMounted(async () => { rows.value = await fetchIntegrations() })
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        平台授权
      </h4><p class="text-body-1 mb-0">
        连接状态来自本地演示配置，密钥只保存引用。
      </p>
    </div><VRow>
      <VCol
        v-for="item in rows"
        :key="item.id"
        cols="12"
        md="4"
      >
        <VCard class="h-100">
          <VCardItem>
            <template #prepend>
              <VAvatar
                color="primary"
                variant="tonal"
              >
                <VIcon icon="tabler-plug" />
              </VAvatar>
            </template><VCardTitle>{{ item.name }}</VCardTitle><VCardSubtitle>{{ item.platform }}</VCardSubtitle>
          </VCardItem><VCardText>
            <VChip
              :color="item.status === 'connected' ? 'success' : 'warning'"
              variant="tonal"
            >
              {{ item.status === 'connected' ? '已连接' : '需处理' }}
            </VChip><div class="text-body-2 mt-4">
              账号：{{ item.account }}
            </div><div class="text-caption mt-2">
              最近同步：{{ item.lastSync }}
            </div>
          </VCardText><VCardActions>
            <VBtn variant="text">
              查看配置
            </VBtn><VSpacer /><VBtn
              color="primary"
              variant="tonal"
            >
              重新授权
            </VBtn>
          </VCardActions>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>
