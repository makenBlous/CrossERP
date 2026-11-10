import { setupLayouts } from 'virtual:meta-layouts'
import type { App } from 'vue'
import type { RouteRecordRaw } from 'vue-router/auto'
import { createRouter, createWebHistory } from 'vue-router/auto'
import PlaceholderPage from '@/components/PlaceholderPage.vue'
import { pageCatalog } from '@/config/pages'
import { setupGuards } from '@/plugins/1.router/guards'
import KnowledgePage from '@/views/knowledge/KnowledgePage.vue'
import SettlementSplitPage from '@/pages/finance/settlements/[id]/split.vue'

function recursiveLayouts(route: RouteRecordRaw): RouteRecordRaw {
  // setupLayouts 自己会递归处理 children；每个顶层路由只包一次，避免深链出现嵌套侧栏。
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
    const rootRedirect: RouteRecordRaw = { path: '/', redirect: '/dashboard' }
    const mappedWithoutRoot = mapped.filter(route => route.path !== '/')

    const knowledgeIndex = recursiveLayouts({
      path: '/kb/index',
      name: 'kb-index-search',
      component: KnowledgePage,
      props: { mode: 'index' },
      meta: { pageId: 'K08' },
    })

    const settlementSplit = recursiveLayouts({
      path: '/finance/settlements/:id/split',
      name: 'finance-settlement-split',
      component: SettlementSplitPage,
      meta: { pageId: 'F39' },
    })

    // /kb/index must precede generated /kb/:id routes; otherwise the dynamic
    // route renders the 404 placeholder before the K08 page can match.
    return [rootRedirect, knowledgeIndex, settlementSplit, ...mappedWithoutRoot, ...placeholderRoutes]
  },
})

setupGuards(router)

export { router }

export default function (app: App) {
  app.use(router)
}
