import type { CurrencyCode } from '@/types/domain'

/** 万分位整数。1.2300 = 12300。加减只做整数运算。 */
export type Minor = number

const SCALE = 10000

/** 1 单位外币折合多少 USD，万分位。演示汇率，不是行情接口。 */
export const FX_TO_USD: Record<CurrencyCode, Minor> = {
  USD: 10000,
  EUR: 10800,
  GBP: 12700,
  CNY: 1400,
  JPY: 67,
}

export function minorFromDecimal(text: string): Minor {
  const trimmed = text.trim()
  const negative = trimmed.startsWith('-')
  const raw = trimmed.replace(/^[+-]/, '')
  const [whole, frac = ''] = raw.split('.')

  if (!/^\d+$/.test(whole) || (frac !== '' && !/^\d+$/.test(frac)) || frac.length > 4)
    throw new Error(`金额格式不正确: ${text}`)

  const padded = `${frac}0000`.slice(0, 4)
  const value = Number(whole) * SCALE + Number(padded)

  return negative ? -value : value
}

export function addMinor(left: Minor, right: Minor): Minor {
  return left + right
}

export function mulQty(unit: Minor, qty: number): Minor {
  return unit * qty
}

/** basis points：1500 = 15.00%。结果四舍五入到万分位。 */
export function percentOf(amount: Minor, basisPoints: number): Minor {
  const negative = amount < 0
  const abs = Math.abs(amount)
  const next = Math.round(abs * basisPoints / SCALE)

  return negative ? -next : next
}

export function convertMinor(amount: Minor, from: CurrencyCode, to: CurrencyCode): Minor {
  if (from === to)
    return amount

  const usd = Math.round(amount * FX_TO_USD[from] / SCALE)

  return Math.round(usd * SCALE / FX_TO_USD[to])
}

/** 展示用。JPY 到元，其他币种到分，ROUND_HALF_UP。 */
export function toDisplay(minor: Minor, currency: CurrencyCode): number {
  const digits = currency === 'JPY' ? 0 : 2
  const sign = minor < 0 ? -1 : 1
  const abs = Math.abs(minor)
  const factor = 10 ** (4 - digits)
  const units = Math.floor(abs / factor)
  const remainder = abs % factor
  const rounded = remainder * 2 >= factor ? units + 1 : units

  return sign * rounded / (10 ** digits)
}

export function percentRatio(part: number, total: number): number {
  if (total === 0)
    return 0

  return Math.round(part * 10000 / total) / 100
}
