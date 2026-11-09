import { setupLayouts } from 'virtual:meta-layouts'
import type { App } from 'vue'
import type { RouteRecordRaw } from 'vue-router/auto'
import { createRouter, createWebHistory } from 'vue-router/auto'
import PlaceholderPage from '@/components/PlaceholderPage.vue'
import { pageCatalog } from '@/config/pages'
import { setupGuards } from '@/plugins/1.router/guards'

function recursiveLayouts(route: RouteRecordRaw): RouteRecordRaw {
  if (route.children) {
    for (let i = 0; i < route.children.length; i++)
      route.children[i] = recursiveLayouts(route.children[i])

    return route
  }

  return setupLayouts([route])[0]
}

const placeholderRoutes = pageCatalog
  .filter(item => !item.implemented && !item.path.includes('*'))
  .map(item => recursiveLayouts({
    path: item.path,
    name: `page-${item.id}`,
    component: PlaceholderPage,
    meta: {
      pageId: item.id,
      layout: item.layout,
      public: item.public,
      unauthenticatedOnly: item.unauthenticatedOnly,
    },
  }))

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to) {
    if (to.hash)
      return { el: to.hash, behavior: 'smooth', top: 60 }

    return { top: 0 }
  },
  extendRoutes: pages => {
    const mapped = [...pages].map(route => recursiveLayouts(route))
    const root = mapped.find(route => route.path === '/')

    if (root)
      root.redirect = '/dashboard'

    return [...mapped, ...placeholderRoutes]
  },
})

setupGuards(router)

export { router }

export default function (app: App) {
  app.use(router)
}
