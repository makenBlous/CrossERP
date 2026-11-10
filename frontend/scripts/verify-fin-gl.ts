/* fin-gl 点击验收：使用 agent-browser，参数 --base-url / --shots 可覆盖默认值。 */
import { mkdirSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { resolve as resolvePath } from 'node:path'

const args = process.argv.slice(2)

const valueAfter = (name: string, fallback: string) => {
  const index = args.indexOf(name)

  return index >= 0 && args[index + 1] ? args[index + 1] : fallback
}

const baseUrl = valueAfter('--base-url', 'http://127.0.0.1:4143').replace(/\/$/, '')
const shots = resolvePath(valueAfter('--shots', '../_task/shots'))
const session = `fin-gl-${Date.now()}`
const browserBin = process.env.AGENT_BROWSER_BIN ?? 'D:/make/tools/nodejs/node_global/node_modules/agent-browser/bin/agent-browser-win32-x64.exe'

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

async function open(path: string, shot: string) {
  await browser('open', `${baseUrl}${path}`)
  await browser('wait', '--load', 'networkidle')
  await browser('screenshot', resolvePath(shots, shot))

  return browser('get', 'text', 'body')
}

async function main() {
  await browser('open', `${baseUrl}/login`)
  await browser('eval', 'sessionStorage.setItem(\'crosserp-auth\',\'1\'); sessionStorage.setItem(\'crosserp-role\',\'admin\')')

  let body = await open('/inventory/gl-reconcile', 'I17.png')
  assertContains(body, '库存与总账核对', 'I17 标题')
  assertContains(body, '9,175,001', 'I17 演示核对基准')
  assertContains(body, '有差异', 'I17 差异 KPI')

  body = await open('/finance/opening', 'F38.png')
  assertContains(body, '期初导入与启用', 'F38 标题')
  assertContains(body, '借贷不平或库存金额不齐，启用不可用', 'F38 不平阻止启用')

  const disabled = await browser('eval', 'String(document.querySelector(\'[data-test=opening-activate]\')?.hasAttribute(\'disabled\'))')

  assertContains(disabled, 'true', 'F38 启用按钮禁用')
  await browser('find', 'role', 'button', 'click', '--name', '加载平衡演示数据')
  await browser('wait', '500')
  body = await browser('get', 'text', 'body')
  assertContains(body, '期初试算已平衡', 'F38 平衡演示按钮')

  body = await open('/finance/reversals', 'F41.png')
  assertContains(body, '红字冲销工作台', 'F41 标题')
  assertContains(body, '已过账凭证不能编辑', 'F41 只生成草稿提示')
  await browser('find', 'role', 'button', 'click', '--name', '生成红字草稿')
  await browser('wait', '500')
  body = await browser('get', 'text', 'body')
  assertContains(body, '已创建红字草稿', 'F41 红字草稿创建')

  body = await open('/finance/period-close', 'F28.png')
  await browser('eval', 'document.querySelector(\'.v-expansion-panel-title\')?.click()')
  await browser('wait', '250')
  body = await browser('get', 'text', 'body')
  assertContains(body, '库存台账与库存科目', 'F28 库存核对检查项')
  assertContains(body, '暂估未清', 'F28 暂估检查项')
  await browser('find', 'role', 'button', 'click', '--name', '申请反结账')
  await browser('find', 'label', '反结账原因', 'fill', '演示反结账原因')
  await browser('find', 'label', '影响范围（凭证/报表快照）', 'fill', 'VCH-12 与 statement_snapshot-2026-09')
  await browser('find', 'role', 'button', 'click', '--name', '提交申请')
  await browser('wait', '500')
  body = await browser('get', 'text', 'body')
  assertContains(body, '敏感操作提醒与冷静期已记录', 'F28 申请敏感提醒')
  await browser('eval', 'sessionStorage.setItem(\'crosserp-role\',\'finance\'); location.reload()')
  await browser('wait', '--load', 'networkidle')
  await browser('eval', '[...document.querySelectorAll(\'button\')].find(button => button.textContent?.trim() === \'批准\')?.click()')
  await browser('wait', '500')
  body = await browser('get', 'text', 'body')
  assertContains(body, '原结账人不能批准反结账申请', 'F28 原结账人拒绝')
  await browser('eval', 'sessionStorage.setItem(\'crosserp-role\',\'admin\'); location.reload()')
  await browser('wait', '--load', 'networkidle')
  await browser('eval', '[...document.querySelectorAll(\'button\')].find(button => button.textContent?.trim() === \'批准\')?.click()')
  await browser('wait', '500')
  body = await browser('get', 'text', 'body')
  assertContains(body, '申请人不能批准自己的反结账申请', 'F28 申请人自审拒绝')

  body = await open('/finance/settlements/stl-amz-us-10/split', 'F39.png')
  assertContains(body, '结算清分', 'F39 标题')
  assertContains(body, '53.50', 'F39 原币演示金额')
  assertContains(body, '7.1000', 'F39 单一汇率')
  assertContains(body, '未确认映射', 'F39 未确认映射停留')

  const errors = await browser('errors')
  if (errors.trim() && !errors.includes('No errors'))
    throw new Error(`点击验收发现浏览器错误：${errors}`)

  await browser('close')
  console.log(`截图目录：${shots}`)
  console.log('== PASS fin-gl 点击验收 ==')
}

main().catch(error => {
  console.error(error instanceof Error ? error.message : error)
  process.exitCode = 1
})
