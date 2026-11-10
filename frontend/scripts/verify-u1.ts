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
const costs = read('src/pages/catalog/costs.vue')
const fxRates = read('src/pages/finance/fx-rates.vue')
const financeTablePage = read('src/views/finance/FinanceTablePage.vue')

assert(router.includes('return setupLayouts([route])[0]'), '带 children 的父路由也必须经过 setupLayouts')
assert(!/function recursiveLayouts[\s\S]*?return route\s*\}/.test(router), 'recursiveLayouts 不能直接返回未包装的父路由')
assert(listPage.includes('v-if="$slots.actions"'), 'ListPage 必须提供标题行 actions 插槽')
assert(listPage.includes('<slot name="actions" />'), 'ListPage 必须渲染 actions 插槽')
assert(calendar.includes('initialView: isNarrow.value ? \'listMonth\' : \'dayGridMonth\''), '窄屏必须提供列表视图')
assert(calendar.includes('height: \'100%\''), '日历必须使用容器可用高度')
assert(calendar.includes('dayMaxEvents: isNarrow.value ? false : 2'), '桌面月视图必须限制事件行并显示更多入口')
assert(calendar.includes('dayMaxEventRows: isNarrow.value ? false : 2'), '桌面月视图必须限制事件行并显示更多入口')
assert(calendar.includes(`moreLinkContent: ({ num }) => \`+${String.fromCharCode(36)}{num} 更多\``), '更多入口必须显示 +N 更多')
assert(/watch\(isNarrow[\s\S]*?changeView/.test(calendar), '断点变化时必须调用 FullCalendar changeView')
assert(!/:deep\(\.fc-daygrid-day-frame\)[\s\S]*?overflow: hidden/.test(calendar), '日历日期框不得强制裁剪内容')
assert(!/:deep\(\.fc-daygrid-day-events\)[\s\S]*?overflow: hidden/.test(calendar), '日历事件容器不得强制裁剪内容')
assert(calendar.includes('@media (max-width: 767.98px)'), '日历必须有窄屏布局')
assert(costs.includes('<template #actions>'), '成本列表必须使用 ListPage actions 插槽')
assert(!costs.includes('d-flex flex-wrap justify-end gap-3 mb-4'), '成本列表不得在 ListPage 外单独渲染操作行')
assert(fxRates.includes('<template #actions>'), '汇率列表必须使用 FinanceTablePage actions 插槽')
assert(!fxRates.includes('d-flex justify-end mb-4'), '汇率列表不得在 FinanceTablePage 外单独渲染操作行')
assert(financeTablePage.includes('<slot name="actions" />'), 'FinanceTablePage 必须透传 actions 插槽')

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
