import type { App } from 'vue'
import { createI18n } from 'vue-i18n'
import { uiMessages } from './ui'
import { pageCatalog } from '@/config/pages'
import type { AppLocale } from '@/types/domain'
import { themeConfig } from '@themeConfig'

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
