<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchTokens } from '@/api/account'; import { useMockDbStore } from '@/stores/mockdb'; import { useSessionStore } from '@/stores/session'; import type { Actor } from '@/types/entities'

const store = useMockDbStore(); const session = useSessionStore(); const rows = ref<any[]>([]); const dialog = ref(false); const name = ref(''); const plain = ref(''); async function load() { rows.value = await fetchTokens() }; onMounted(load); function actor(): Actor { return { name: session.displayName, role: session.role, at: new Date().toISOString() } }; function create() {
  const result = store.createToken(name.value || '新 Token', actor())

  plain.value = result?.secret ?? ''; dialog.value = false; name.value = ''; load()
}; function revoke(id: string) { store.revokeToken(id, actor()); load() }
</script>

<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h4 class="text-h4">
          我的 API Token
        </h4><p class="text-body-1 mb-0">
          明文只在创建时显示一次，之后仅保留掩码。
        </p>
      </div><VBtn
        color="primary"
        prepend-icon="tabler-plus"
        @click="dialog = true"
      >
        创建 Token
      </VBtn>
    </div><VCard>
      <VTable>
        <thead><tr><th>名称</th><th>Token</th><th>创建时间</th><th>最近使用</th><th>状态</th><th /></tr></thead><tbody>
          <tr
            v-for="item in rows"
            :key="item.id"
          >
            <td>{{ item.name }}</td><td><code>{{ item.prefix }}</code></td><td>{{ item.createdAt }}</td><td>{{ item.lastUsedAt || '尚未使用' }}</td><td>
              <VChip
                size="small"
                :color="item.revoked ? 'secondary' : 'success'"
                variant="tonal"
              >
                {{ item.revoked ? '已撤销' : '有效' }}
              </VChip>
            </td><td>
              <VBtn
                v-if="!item.revoked"
                size="small"
                variant="text"
                color="error"
                @click="revoke(item.id)"
              >
                撤销
              </VBtn>
            </td>
          </tr>
        </tbody>
      </VTable><VCardText v-if="!rows.length">
        还没有 Token。
      </VCardText>
    </VCard><VDialog
      v-model="dialog"
      max-width="420"
    >
      <VCard title="创建 API Token">
        <VCardText>
          <AppTextField
            v-model="name"
            label="名称"
          />
        </VCardText><VCardActions>
          <VSpacer /><VBtn
            variant="text"
            @click="dialog = false"
          >
            取消
          </VBtn><VBtn
            color="primary"
            @click="create"
          >
            创建
          </VBtn>
        </VCardActions>
      </VCard>
    </VDialog><VDialog
      :model-value="Boolean(plain)"
      max-width="520"
      @update:model-value="!$event && (plain = '')"
    >
      <VCard title="请立即保存 Token">
        <VCardText>
          <VAlert
            type="warning"
            variant="tonal"
          >
            关闭后将无法再次查看明文。
          </VAlert><code class="d-block pa-4 mt-4 bg-grey-100">{{ plain }}</code>
        </VCardText><VCardActions>
          <VSpacer /><VBtn
            color="primary"
            @click="plain = ''"
          >
            我已保存
          </VBtn>
        </VCardActions>
      </VCard>
    </VDialog>
  </div>
</template>
