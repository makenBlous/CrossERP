import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

const root = process.cwd()
const src = join(root, 'src')

function read(path: string) {
  return readFileSync(join(root, path), 'utf8')
}

function assert(condition: boolean, message: string) {
  if (!condition)
    throw new Error(`[U1] ${message}`)
}

const router = read('src/plugins/1.router/index.ts')
const listPage = read('src/components/biz/ListPage.vue')
const calendar = read('src/pages/dashboard/calendar.vue')

assert(router.includes('return setupLayouts([route])[0]'), '带 children 的父路由也必须经过 setupLayouts')
assert(!/function recursiveLayouts[\s\S]*?return route\s*\}/.test(router), 'recursiveLayouts 不能直接返回未包装的父路由')
assert(listPage.includes('v-if="$slots.actions"'), 'ListPage 必须提供标题行 actions 插槽')
assert(listPage.includes('<slot name="actions" />'), 'ListPage 必须渲染 actions 插槽')
assert(calendar.includes('initialView: isNarrow.value ? \'listMonth\' : \'dayGridMonth\''), '窄屏必须提供列表视图')
assert(calendar.includes('height: \'100%\''), '日历必须使用容器可用高度')
assert(calendar.includes('dayMaxEvents: isNarrow.value ? false : 2'), '桌面月视图必须限制事件行并显示更多入口')
assert(calendar.includes('@media (max-width: 767.98px)'), '日历必须有窄屏布局')

function collectVue(dir: string): string[] {
  const entries = readdirSync(dir)

  return entries.flatMap(name => {
    const path = join(dir, name)
    if (statSync(path).isDirectory())
      return collectVue(path)

    return name.endsWith('.vue') ? [path] : []
  })
}

const pageFiles = collectVue(join(src, 'pages'))

const listPagesWithStandaloneActions = pageFiles.filter(path => {
  const text = readFileSync(path, 'utf8')

  return text.includes('<ListPage') && text.includes('d-flex justify-end mb-4')
})

const allowedStandalone = new Set([
  'pages/dashboard/stores.vue',
  'pages/finance/fx-rates.vue',
  'pages/finance/recon/index.vue',
])

const unexpected = listPagesWithStandaloneActions
  .map(path => relative(src, path).replaceAll('\\', '/'))
  .filter(path => !allowedStandalone.has(path))

assert(unexpected.length === 0, `列表页仍有独占一行的操作按钮：${unexpected.join(', ')}`)

const migrated = [
  'src/pages/inventory/outbound.vue',
  'src/pages/inventory/transfers.vue',
  'src/pages/catalog/skus/index.vue',
  'src/pages/procurement/orders/index.vue',
]

for (const path of migrated)
  assert(read(path).includes('<template #actions>'), `${path} 必须使用 ListPage actions 插槽`)

console.log('[U1] static checks passed')
