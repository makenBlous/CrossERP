import type { CurrencyCode } from '@/types/domain'

const currencyLocale: Record<CurrencyCode, string> = {
  USD: 'en-US',
  EUR: 'de-DE',
  GBP: 'en-GB',
  CNY: 'zh-CN',
}

export function formatMoney(amount: number, currency: CurrencyCode) {
  return new Intl.NumberFormat(currencyLocale[currency], {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

export function formatPercent(value: number) {
  return `${value.toFixed(2)}%`
}

export function formatInteger(value: number) {
  return new Intl.NumberFormat('zh-CN').format(value)
}
