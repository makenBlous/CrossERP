import type { App, DirectiveBinding } from 'vue'
import { useSessionStore } from '@/stores/session'
import type { Role } from '@/types/domain'
import type { AppAction } from '@/utils/permission'
import { can } from '@/utils/permission'

const stops = new WeakMap<HTMLElement, () => void>()

function apply(el: HTMLElement, binding: DirectiveBinding<AppAction>, role: Role) {
  const allowed = can(role, binding.value)

  if (binding.modifiers.disable) {
    el.toggleAttribute('disabled', !allowed)
    el.setAttribute('aria-disabled', allowed ? 'false' : 'true')

    return
  }

  el.style.display = allowed ? '' : 'none'
}

export default function (app: App) {
  app.directive('can', {
    mounted(el, binding: DirectiveBinding<AppAction>) {
      const session = useSessionStore()
      const host = el as HTMLElement
      const run = () => apply(host, binding, session.role)

      run()
      stops.set(host, watch(() => session.role, run))
    },
    updated(el, binding: DirectiveBinding<AppAction>) {
      const session = useSessionStore()

      apply(el as HTMLElement, binding, session.role)
    },
    unmounted(el) {
      stops.get(el as HTMLElement)?.()
      stops.delete(el as HTMLElement)
    },
  })
}
