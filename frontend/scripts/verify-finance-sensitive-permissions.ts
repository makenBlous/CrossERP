/* 财务敏感页：菜单 requiredPermissions 必须覆盖真实接口权限。 */
import { createPinia, setActivePinia } from 'pinia'
import { fetchAp, fetchApAging, fetchCash, fetchClearing } from '@/api/finance'
import { canRoleOpen, findPageByPath } from '@/config/pages'
import { roleTemplates } from '@/config/permissions'
import { useSessionStore } from '@/stores/session'
import type { Role } from '@/types/domain'

const memoryStorage = () => {
  const values = new Map<string, string>()

  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, String(value)),
    removeItem: (key: string) => values.delete(key),
    clear: () => values.clear(),
    key: (index: number) => [...values.keys()][index] ?? null,
    get length() { return values.size },
  }
}

;(globalThis as any).sessionStorage = memoryStorage()
;(globalThis as any).localStorage = memoryStorage()
setActivePinia(createPinia())

const session = useSessionStore()
const roles: Role[] = ['admin', 'operator', 'finance', 'viewer', 'auditor', ...roleTemplates.map(item => item.id as Role)]
const pages = ['/finance/ap', '/finance/cash', '/finance/clearing'] as const
const calls = { '/finance/ap': [fetchAp, fetchApAging], '/finance/cash': [fetchCash], '/finance/clearing': [fetchClearing] } as const
let failures = 0

function as(role: Role) {
  session.setRole(role)
}
function ok(label: string, condition: boolean) {
  if (!condition)
    failures += 1
  console.log(`${condition ? 'PASS' : 'FAIL'} ${label}`)
}

for (const path of pages) {
  const page = findPageByPath(path)
  if (!page) {
    ok(`页面存在 ${path}`, false)
    continue
  }
  const expectedPermission = path === '/finance/ap' ? 'accounts_payable:read' : 'payment_entry:read'

  ok(`${path} 页面声明 ${expectedPermission}`, page.requiredPermissions?.includes(expectedPermission) === true)
}

for (const role of roles) {
  as(role)
  for (const path of pages) {
    const page = findPageByPath(path)!
    const menu = canRoleOpen(role, page)
    for (const call of calls[path]) {
      let allowed = true
      try {
        await call()
      }
      catch {
        allowed = false
      }
      ok(`${role} ${path} 菜单与接口一致`, menu === allowed)
    }
  }
}

for (const role of ['customer_service', 'advertising', 'external_viewer'] as Role[]) {
  as(role)
  await Promise.all([fetchAp, fetchApAging].map(call => call()
    .then(() => {
      ok(`${role} 应付被拒绝`, false)
    })
    .catch(() => {
      ok(`${role} 应付被拒绝`, true)
    })))
}

as('external_viewer')
await fetchAp()
  .then(() => {
    ok('只有 report:read 的角色读应付被拒绝', false)
  })
  .catch(() => {
    ok('只有 report:read 的角色读应付被拒绝', true)
  })

console.log(`== FAIL ${failures}`)
process.exit(failures ? 1 : 0)
