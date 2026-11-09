import type { CurrencyCode } from '@/types/domain'

const currencyLocale: Record<CurrencyCode, string> = {
  USD: 'en-US',
  EUR: 'de-DE',
  GBP: 'en-GB',
  CNY: 'zh-CN',
  JPY: 'ja-JP',
}

const currencyDigits: Record<CurrencyCode, number> = {
  USD: 2,
  EUR: 2,
  GBP: 2,
  CNY: 2,
  JPY: 0,
}

export function formatMoney(amount: number, currency: CurrencyCode) {
  const digits = currencyDigits[currency]

  return new Intl.NumberFormat(currencyLocale[currency], {
    style: 'currency',
    currency,
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(amount)
}

export function formatPercent(value: number) {
  return `${value.toFixed(2)}%`
}

export function formatInteger(value: number) {
  return new Intl.NumberFormat('zh-CN').format(value)
}
