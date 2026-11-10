import assert from 'node:assert/strict'
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

// 文件路由结构检查：
// 1. foo.vue 与同名目录 foo/ 并存时，foo.vue 是父路由，必须渲染 <RouterView>（或按 route.path 显式切换子页面，如批次 B 的列表/详情页），否则子页面不可达；
// 2. index.vue 不得与 index/ 目录并存（index 目录同样映射为空段，会与 index.vue 生成同一路径的重复记录）。
const pagesDir = fileURLToPath(new URL('../src/pages', import.meta.url))
const problems: string[] = []
let parents = 0

function walk(dir: string) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) {
      walk(full)
      continue
    }
    if (!entry.endsWith('.vue'))
      continue
    const base = entry.slice(0, -4)
    const sibling = join(dir, base)
    if (!existsSync(sibling) || !statSync(sibling).isDirectory())
      continue
    parents += 1
    if (base === 'index')
      problems.push(`${full} 与 index/ 目录并存`)
    else if (!/<RouterView|<router-view/.test(readFileSync(full, 'utf8')) && !/useRoute\(\)[\s\S]*route\.path/.test(readFileSync(full, 'utf8')))
      problems.push(`${full} 是父路由但既没有 RouterView 也没有按 route.path 切换子页面`)
  }
}

walk(pagesDir)

assert.deepEqual(problems, [], `文件路由结构问题：${JSON.stringify(problems)}`)

console.log(`[通过] ${parents} 个父路由均渲染 RouterView，无 index/ 重复目录`)
