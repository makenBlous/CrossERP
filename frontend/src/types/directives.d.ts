import type { AppAction } from '@/utils/permission'

export {}

declare module 'vue' {
  interface ComponentCustomProperties {
    vCan?: AppAction
  }

  interface GlobalDirectives {
    vCan: AppAction
  }
}
