import type { App } from 'vue'
import { createI18n } from 'vue-i18n'
import { uiMessages } from './ui'
import { approvalsMessages } from './approvals'
import { adsMessages } from './ads'
import { financeMessages } from './finance'
import { pageCatalog } from '@/config/pages'
import type { AppLocale } from '@/types/domain'
import { themeConfig } from '@themeConfig'

// 批次 2 的模块文案与 ui.ts 里已有的同名分组合并，避免覆盖第 1 批已有的键。
function uiSection(locale: AppLocale, key: string): Record<string, unknown> {
  const section = (uiMessages[locale] as Record<string, unknown>)[key]

  return section && typeof section === 'object' ? section as Record<string, unknown> : {}
}

function messagesFor(locale: AppLocale) {
  const page: Record<string, { name: string; purpose: string }> = {}

  for (const item of pageCatalog) {
    page[item.id] = {
      name: item.name[locale],
      purpose: item.purpose[locale],
    }
  }

  return {
    ...uiMessages[locale],
    finance: { ...uiSection(locale, 'finance'), ...financeMessages[locale] },
    ads: { ...uiSection(locale, 'ads'), ...adsMessages[locale] },
    approvals: { ...uiSection(locale, 'approvals'), ...approvalsMessages[locale] },
    page,
  }
}

const i18n = createI18n({
  legacy: false,
  locale: themeConfig.app.i18n.defaultLocale,
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': messagesFor('zh-CN'),
    'en': messagesFor('en'),
  },
})

export default function (app: App) {
  app.use(i18n)
}
