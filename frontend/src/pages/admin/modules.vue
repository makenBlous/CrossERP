<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchModules } from '@/api/admin'; import { database } from '@/api/mock-client'

const rows = ref<any[]>([])

onMounted(async () => { rows.value = await fetchModules() }); function toggle(item: any) { item.enabled = !item.enabled; database().persist() }
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        模块管理
      </h4><p class="text-body-1 mb-0">
        打开或关闭后期模块，只影响菜单和接口，不删数据。
      </p>
    </div><VRow>
      <VCol
        v-for="item in rows"
        :key="item.id"
        cols="12"
        sm="6"
        md="3"
      >
        <VCard class="h-100">
          <VCardItem><VCardTitle>{{ item.name }}</VCardTitle><VCardSubtitle>{{ item.enabled ? '已启用' : '未启用' }}</VCardSubtitle></VCardItem><VCardText class="text-body-2">
            {{ item.description }}
          </VCardText><VCardActions>
            <VSwitch
              :model-value="item.enabled"
              color="primary"
              hide-details
              @update:model-value="toggle(item)"
            />
          </VCardActions>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>
