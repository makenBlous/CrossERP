<script setup lang="ts">
import { changePassword } from '@/api/account'

const form = reactive({ current: '', next: '', confirm: '' })
const saved = ref(false)

async function save() {
  if (!form.next || form.next !== form.confirm)
    return
  await changePassword()
  form.current = ''
  form.next = ''
  form.confirm = ''
  saved.value = true
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        修改密码
      </h4><p class="text-body-1 mb-0">
        保存时只记录安全日志，永远不保存密码明文。
      </p>
    </div><VCard max-width="620">
      <VCardText>
        <VAlert
          v-if="saved"
          type="success"
          variant="tonal"
          class="mb-4"
        >
          密码已更新。
        </VAlert><VTextField
          v-model="form.current"
          type="password"
          label="当前密码"
          class="mb-4"
        /><VTextField
          v-model="form.next"
          type="password"
          label="新密码"
          class="mb-4"
        /><VTextField
          v-model="form.confirm"
          type="password"
          label="确认新密码"
        />
      </VCardText><VCardActions>
        <VSpacer /><VBtn
          color="primary"
          @click="save"
        >
          更新密码
        </VBtn>
      </VCardActions>
    </VCard>
  </div>
</template>
