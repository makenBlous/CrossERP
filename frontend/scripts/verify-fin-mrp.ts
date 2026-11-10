/* fin-mrp 点击验收：使用 agent-browser 可执行文件直接拉起，参数 --base-url / --shots 可覆盖默认值。 */
import { mkdirSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { resolve as resolvePath } from 'node:path'

const args = process.argv.slice(2)

const valueAfter = (name: string, fallback: string) => {
  const index = args.indexOf(name)

  return index >= 0 && args[index + 1] ? args[index + 1] : fallback
}

const baseUrl = valueAfter('--base-url', 'http://127.0.0.1:4144').replace(/\/$/, '')
const shots = resolvePath(valueAfter('--shots', '../_task/shots'))
const session = `fin-mrp-${Date.now()}`
const browserBin = process.env.AGENT_BROWSER_BIN ?? 'D:/make/tools/nodejs/node_global/node_modules/agent-browser/bin/agent-browser-win32-x64.exe'
const planId = 'rp-2026-11-11-v3'

mkdirSync(shots, { recursive: true })

async function browser(command: string, ...commandArgs: string[]) {
  return new Promise<string>((resolve, reject) => {
    const child = spawn(browserBin, ['--session', session, command, ...commandArgs], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true })
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

function assertContains(text: string, expected: string, label: string) {
  if (!text.includes(expected))
    throw new Error(`${label} 未找到：${expected}`)
  console.log(`PASS ${label}`)
}

async function clickTest(testId: string) {
  await browser('eval', `document.querySelector('[data-test="${testId}"]')?.click(); 'clicked'`)
}

async function main() {
  await browser('open', `${baseUrl}/login`)
  await browser('eval', 'sessionStorage.setItem(\'crosserp-auth\',\'1\'); sessionStorage.setItem(\'crosserp-role\',\'admin\')')
  await browser('eval', 'localStorage.removeItem(\'crosserp-replenishment-v1\')')

  await browser('open', `${baseUrl}/inventory/replenishment/plans`)
  await browser('wait', '--load', 'networkidle')
  let body = await browser('get', 'text', 'body')
  assertContains(body, '补货计划版本', 'I19 标题')
  assertContains(body, 'V3', 'I19 演示版本号')
  assertContains(body, '冻结行', 'I19 冻结行列')
  await browser('screenshot', resolvePath(shots, 'plans.png'))

  await clickTest(`open-replenishment-version-${planId}`)
  await browser('wait', '--load', 'networkidle')
  await browser('wait', '400')
  body = await browser('get', 'text', 'body')
  assertContains(body, '补货计划版本详情 · V3', 'I20 标题')
  assertContains(body, '供给快照', 'I20 供给快照')
  assertContains(body, '必断货只提示，不计入采购量。', 'I20 必断货提示')
  assertContains(body, '制单人不能审批自己的采购单。', 'I20 采购自审提示')
  assertContains(body, 'AI 建议系数（未批准，不进公式）', 'I20 AI 系数提示')
  await browser('screenshot', resolvePath(shots, 'plan-detail.png'))

  await clickTest(`detail-freeze-${planId}-line-2`)
  await browser('wait', '600')
  body = await browser('get', 'text', 'body')
  assertContains(body, '解冻', 'I20 冻结后可解冻')

  await clickTest(`detail-draft-${planId}-line-1`)
  await browser('wait', '800')
  body = await browser('get', 'text', 'body')
  assertContains(body, '采购申请草稿已生成，等待人工审批。', 'I20 生成草稿成功')
  assertContains(body, '已生成草稿', 'I20 行上草稿标记')
  await browser('screenshot', resolvePath(shots, 'draft.png'))

  assertContains(body, '建议人不能批准自己的系数', 'I20 系数自审规则')
  await browser('screenshot', resolvePath(shots, 'self-approval-rule.png'))

  const errors = await browser('errors')
  if (errors.trim() && !errors.includes('No errors') && !/^No page errors/i.test(errors.trim()))
    throw new Error(`点击验收发现浏览器错误：${errors}`)

  await browser('close')
  console.log(`截图目录：${shots}`)
  console.log('== PASS fin-mrp 点击验收 ==')
}

main().catch(error => {
  console.error(error instanceof Error ? error.message : error)
  process.exitCode = 1
})
