import { defineStore } from 'pinia'
import { computeEffectivePermissions, narrowAiPermissions } from '@/utils/permission-engine'
import type { EffectivePermission, PermissionSubject, TemporaryGrant, UserPermissionOverride } from '@/types/foundation'

const OVERRIDE_KEY = 'crosserp-permission-overrides'

function readOverrides<T>(key: string): T[] {
  if (typeof sessionStorage === 'undefined')
    return []
  try {
    return JSON.parse(sessionStorage.getItem(key) ?? '[]') as T[]
  }
  catch {
    return []
  }
}

export const usePermissionStore = defineStore('permissions', {
  state: () => ({
    overrides: readOverrides<UserPermissionOverride>(OVERRIDE_KEY),
    temporaryGrants: [] as TemporaryGrant[],
    aiNarrowing: {} as Record<string, string[]>,
  }),
  getters: {
    effective: state => (subject: PermissionSubject): EffectivePermission[] => computeEffectivePermissions({
      ...subject,
      overrides: state.overrides,
      temporaryGrants: state.temporaryGrants,
    }),
  },
  actions: {
    saveOverride(override: UserPermissionOverride) {
      this.overrides = [...this.overrides.filter(item => item.id !== override.id), override]
      if (typeof sessionStorage !== 'undefined')
        sessionStorage.setItem(OVERRIDE_KEY, JSON.stringify(this.overrides))
    },
    clearExpired(now = Date.now()) {
      this.temporaryGrants = this.temporaryGrants.filter(item => !item.expiresAt || Date.parse(item.expiresAt) > now)
    },
    aiEffective(subject: PermissionSubject, agentId?: string) {
      return narrowAiPermissions(this.effective(subject), agentId ? this.aiNarrowing[agentId] : undefined)
    },
  },
})
