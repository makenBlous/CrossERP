export interface ConfirmOptions {
  title: string
  text: string
  confirmText: string
  cancelText: string
}

interface PendingConfirm {
  options: ConfirmOptions
  resolve: (value: boolean) => void
}

const pending = ref<PendingConfirm | null>(null)

export function useConfirm() {
  function confirm(options: ConfirmOptions) {
    return new Promise<boolean>(resolve => {
      pending.value = { options, resolve }
    })
  }

  function settle(value: boolean) {
    pending.value?.resolve(value)
    pending.value = null
  }

  return { confirm, pending, settle }
}
