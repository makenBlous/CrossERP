<script setup lang="ts">
import { useConfirm } from '@/composables/useConfirm'

const { pending, settle } = useConfirm()
const { t } = useI18n({ useScope: 'global' })
const last = ref<{ title: string; text: string; confirmText: string; cancelText: string } | null>(null)

watch(pending, value => {
  if (value)
    last.value = value.options
})

function onConfirm(value: boolean) {
  settle(value)
}

function onVisible(open: boolean) {
  if (!open && pending.value)
    settle(false)
}
</script>

<template>
  <!-- 复用 Vuexy ConfirmDialog。第一次点确认/取消就结束 Promise，后续成功/取消提示由该组件自己弹出。 -->
  <ConfirmDialog
    :is-dialog-visible="pending != null"
    :confirmation-question="last?.text || last?.title || ''"
    :confirm-title="last?.title || ''"
    :confirm-msg="last?.text || ''"
    :cancel-title="last?.cancelText || t('foundation.cancel')"
    :cancel-msg="last?.text || ''"
    :confirm-text="last?.confirmText || t('foundation.confirm')"
    :cancel-text="last?.cancelText || t('foundation.cancel')"
    :ok-text="t('foundation.confirm')"
    @confirm="onConfirm"
    @update:is-dialog-visible="onVisible"
  />
</template>
