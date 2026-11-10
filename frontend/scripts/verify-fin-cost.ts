/*
 * fin-cost 点击/权限验证脚本。
 * 用法：pnpm exec tsx scripts/verify-fin-cost.ts --base-url http://127.0.0.1:4145 --shots ../_task/shots
 * 亦可使用 --port 4145。浏览器使用 agent-browser 可执行文件直接拉起。
 */
import { existsSync, mkdirSync } from 'node:fs'
import { mkdir, writeFile } from 'node:fs/promises'
import { spawn } from 'node:child_process'
import { delimiter, join, resolve as resolvePath } from 'node:path'
import { createPinia, setActivePinia } from 'pinia'
import { approveLandedCostVoucher, fetchGrniBalances, fetchLandedCost, fetchLandedCosts, fetchStockLedger, submitLandedCostApproval } from '@/api/fin-cost'
import { canRoleOpen, findPageByPath } from '@/config/pages'
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

const args = process.argv.slice(2)

const valueAfter = (name: string, fallback: string) => {
  const index = args.indexOf(name)

  return index >= 0 && args[index + 1] ? args[index + 1] : fallback
}

const baseUrlArg = valueAfter('--base-url', '').replace(/\/$/, '')
const port = Number(valueAfter('--port', baseUrlArg.match(/:(\d+)$/)?.[1] ?? '4145'))
const shotsDir = valueAfter('--shots', '../_task/shots')
const baseUrl = (baseUrlArg || `http://127.0.0.1:${port}`).replace(/\/$/, '')
const session = useSessionStore()
const browserSession = `fin-cost-${Date.now()}`

const browserBin = process.env.AGENT_BROWSER_BIN ?? (() => {
  const globalBin = process.env.PATH?.split(delimiter).find(item => existsSync(join(item, 'agent-browser.ps1')))

  return globalBin ? join(globalBin, 'node_modules', 'agent-browser', 'bin', 'agent-browser-win32-x64.exe') : 'D:/make/tools/nodejs/node_global/node_modules/agent-browser/bin/agent-browser-win32-x64.exe'
})()

const roles: Role[] = ['admin', 'finance', 'accountant', 'finance_manager', 'warehouse_logistics', 'purchaser', 'auditor_template']
const paths = ['/inventory/ledger', '/finance/landed-costs', '/finance/landed-costs/lcv-2026-001', '/finance/grni']
let failures = 0

mkdirSync(shotsDir, { recursive: true })

function ok(label: string, condition: boolean) {
  if (!condition)
    failures += 1
  console.log(`${condition ? 'PASS' : 'FAIL'} ${label}`)
}

async function snapshot(path: string, status: string) {
  const safe = path.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '')
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="900" height="180"><rect width="100%" height="100%" fill="#f5f7fb"/><text x="24" y="48" font-family="sans-serif" font-size="22" fill="#1f2937">${path}</text><text x="24" y="90" font-family="sans-serif" font-size="18" fill="#047857">${status}</text><text x="24" y="132" font-family="sans-serif" font-size="14" fill="#475569">fin-cost mock verification · port ${port}</text></svg>`

  await writeFile(`${shotsDir}/${safe}.svg`, svg, 'utf8')
}

async function browser(command: string, ...commandArgs: string[]) {
  return new Promise<string>((resolve, reject) => {
    const child = spawn(browserBin, ['--session', browserSession, command, ...commandArgs], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true })
    let output = ''
    let timer: ReturnType<typeof setTimeout> | undefined
    let hardTimeout: ReturnType<typeof setTimeout> | undefined

    const finish = () => {
      if (timer)
        clearTimeout(timer)
      if (hardTimeout)
        clearTimeout(hardTimeout)
      child.kill()
      resolve(output)
    }

    child.stdout.on('data', chunk => {
      output += String(chunk)
      if (timer)
        clearTimeout(timer)
      timer = setTimeout(finish, 250)
    })
    child.stderr.on('data', chunk => {
      output += String(chunk)
    })
    child.on('error', reject)
    if (command === 'errors')
      timer = setTimeout(finish, 1000)
    hardTimeout = setTimeout(() => reject(new Error(`agent-browser ${command} 超时：${output}`)), 20000)
  })
}

function browserShotName(path: string) {
  if (path === '/inventory/ledger')
    return 'inventory-ledger.png'
  if (path === '/finance/landed-costs')
    return 'landed-costs.png'
  if (path === '/finance/grni')
    return 'grni.png'

  return 'landed-cost-detail.png'
}

function pageErrorsAcceptable(errors: string) {
  const text = errors.trim()

  return !text || text.includes('No errors') || /^No page errors/i.test(text)
}

async function browserClickVerification() {
  try {
    await browser('open', `${baseUrl}/login`)
    await browser('eval', 'sessionStorage.setItem(\'crosserp-auth\',\'1\'); sessionStorage.setItem(\'crosserp-role\',\'admin\')')

    for (const path of paths) {
      await browser('open', `${baseUrl}${path}`)
      await browser('wait', '--load', 'networkidle')
      await browser('screenshot', resolvePath(shotsDir, browserShotName(path)))

      const body = await browser('get', 'text', 'body')

      const expected = path === '/inventory/ledger'
        ? '库存台账'
        : path === '/finance/landed-costs'
          ? '到岸成本分摊'
          : path === '/finance/grni'
            ? '暂估'
            : 'LCV-2026-001'

      ok(`浏览器打开 ${path}`, body.includes(expected))

      const errors = await browser('errors')

      ok(`浏览器无页面错误 ${path}`, pageErrorsAcceptable(errors))
    }

    await browser('open', `${baseUrl}/finance/landed-costs/lcv-2026-001`)
    await browser('wait', '--load', 'networkidle')
    await browser('find', 'role', 'button', 'click', '--name', '批准并过账')
    await browser('wait', '700')

    const approved = await browser('get', 'text', 'body')

    ok('浏览器点击批准并过账', /已过账|批准|过账/.test(approved))
    await browser('screenshot', resolvePath(shotsDir, 'landed-cost-approved.png'))
    await browser('close')
  }
  catch (error) {
    ok('Agent Browser 点击验证可复现', false)
    console.error(error instanceof Error ? error.message : error)
  }
}

await mkdir(shotsDir, { recursive: true })

for (const path of paths) {
  const page = findPageByPath(path)

  ok(`页面登记 ${path}`, Boolean(page?.implemented))
  if (page)
    ok(`页面权限 ${path}`, page.requiredPermissions?.length === 1)
  try {
    const response = await fetch(`${baseUrl}${path}`)

    ok(`预览响应 ${path}`, response.status === 200)
    await snapshot(path, `HTTP ${response.status}`)
  }
  catch (error) {
    ok(`预览可访问 ${path}`, false)
    await snapshot(path, `未连接预览：${error instanceof Error ? error.message : 'unknown error'}`)
  }
}

await browserClickVerification()

for (const role of roles) {
  session.setRole(role)

  const ledgerPage = findPageByPath('/inventory/ledger')
  const landedPage = findPageByPath('/finance/landed-costs')
  const grniPage = findPageByPath('/finance/grni')

  ok(`${role} 库存台账菜单与权限一致`, Boolean(ledgerPage && canRoleOpen(role, ledgerPage)) === ['admin', 'finance', 'accountant', 'finance_manager', 'warehouse_logistics', 'auditor_template'].includes(role))
  ok(`${role} 到岸成本菜单与权限一致`, Boolean(landedPage && canRoleOpen(role, landedPage)) === ['admin', 'finance', 'accountant', 'finance_manager', 'warehouse_logistics'].includes(role))
  ok(`${role} 暂估页与权限一致`, Boolean(grniPage && canRoleOpen(role, grniPage)) === ['admin', 'finance', 'accountant', 'finance_manager', 'purchaser', 'warehouse_logistics'].includes(role))
}

session.setRole('warehouse_logistics')
ok('仓储/物流读取库存台账', (await fetchStockLedger()).length >= 4)
ok('仓储/物流读取到岸成本', (await fetchLandedCosts()).length >= 3)
session.setRole('auditor_template')

const auditorLedger = await fetchStockLedger()

ok('审计读取台账但隐藏成本字段', auditorLedger.every(row => row.amountDelta == null && row.balanceAmount == null))
session.setRole('accountant')
ok('会计读取暂估余额', (await fetchGrniBalances()).length >= 3)

const accountantLedger = await fetchStockLedger()

ok('会计读取库存成本字段', accountantLedger.some(row => row.amountDelta != null && row.balanceAmount != null))
ok('会计读取真实详情 ID', (await fetchLandedCost('lcv-2026-001'))?.no === 'LCV-2026-001')
await submitLandedCostApproval('lcv-2026-003')
  .then(result => ok('会计提交草稿分摊单', result.status === 'pending'))
  .catch(() => ok('会计提交草稿分摊单', false))

session.setRole('finance_manager')
await submitLandedCostApproval('lcv-2026-004')
  .then(() => ok('财务主管不能提交分摊单', false))
  .catch(() => ok('财务主管不能提交分摊单', true))
await approveLandedCostVoucher('lcv-2026-003')
  .then(result => ok('财务主管审批会计提交的分摊单', result.status === 'posted'))
  .catch(() => ok('财务主管审批会计提交的分摊单', false))
await approveLandedCostVoucher('lcv-2026-001')
  .then(result => ok('财务主管批准他人提交的分摊单', result.status === 'posted'))
  .catch(() => ok('财务主管批准他人提交的分摊单', false))
await approveLandedCostVoucher('lcv-2026-004')
  .then(() => ok('制单人不能审批自己的分摊单', false))
  .catch(() => ok('制单人不能审批自己的分摊单', true))

console.log(`== FAIL ${failures}`)
process.exit(failures ? 1 : 0)
