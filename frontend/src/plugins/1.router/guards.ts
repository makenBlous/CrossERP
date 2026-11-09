import type { Router } from 'vue-router'
import { canRoleOpen, findPageByPath } from '@/config/pages'
import { useSessionStore } from '@/stores/session'
import type { Role } from '@/types/domain'
import { useMockDbStore } from '@/stores/mockdb'

export function setupGuards(router: Router) {
  let subscribed = false

  router.beforeEach(to => {
    const session = useSessionStore()

    if (!subscribed) {
      subscribed = true
      session.$subscribe((_mutation, state) => {
        const current = findPageByPath(router.currentRoute.value.path)

        if (current && !current.public && !canRoleOpen(state.role as Role, current))
          router.push('/not-authorized')
      })
    }

    const page = findPageByPath(to.path)
    const isPublic = Boolean(to.meta.public || page?.public)

    if (isPublic) {
      if ((to.meta.unauthenticatedOnly || page?.unauthenticatedOnly) && session.isLoggedIn)
        return '/dashboard'

      return
    }

    if (!session.isLoggedIn) {
      return {
        path: '/login',
        query: to.fullPath === '/' || to.fullPath === '/dashboard' ? {} : { redirect: to.fullPath },
      }
    }

    const override = useMockDbStore().db.roleOverrides?.find(item => item.role === session.role)
    if (page && (override?.hiddenGroups.includes(page.group ?? '') || override?.hiddenPageIds.includes(page.id)))
      return '/not-authorized'
    if (page && !canRoleOpen(session.role, page))
      return '/not-authorized'
  })
}
