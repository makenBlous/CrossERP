import { defineStore } from 'pinia'
import type { AiMode, AiModeState } from '@/types/foundation'

const KEY = 'crosserp-ai-mode'
const initial: AiModeState = { mode: 'normal', changedAt: new Date(0).toISOString(), changedBy: 'seed', reason: '默认正常模式' }

function read(): AiModeState {
  if (typeof sessionStorage === 'undefined')
    return initial
  try {
    return { ...initial, ...(JSON.parse(sessionStorage.getItem(KEY) ?? 'null') as Partial<AiModeState> | null) }
  }
  catch {
    return initial
  }
}

export const useAiModeStore = defineStore('ai-mode', {
  state: () => read(),
  getters: {
    isEnabled: state => state.mode !== 'off',
    isReadOnly: state => state.mode === 'degraded',
  },
  actions: {
    setMode(mode: AiMode, changedBy: string, reason: string) {
      Object.assign(this, { mode, changedBy, reason, changedAt: new Date().toISOString() })
      if (typeof sessionStorage !== 'undefined')
        sessionStorage.setItem(KEY, JSON.stringify(this.$state))
    },
  },
})
