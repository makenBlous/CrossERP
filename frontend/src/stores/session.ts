import { defineStore } from 'pinia'
import type { Role } from '@/types/domain'

const AUTH_KEY = 'crosserp-auth'
const ROLE_KEY = 'crosserp-role'
const NAME_KEY = 'crosserp-name'

const roles: Role[] = ['admin', 'operator', 'finance', 'viewer', 'auditor']

function readStorage(key: string) {
  if (typeof sessionStorage === 'undefined')
    return null

  return sessionStorage.getItem(key)
}

function writeStorage(key: string, value: string) {
  if (typeof sessionStorage === 'undefined')
    return

  sessionStorage.setItem(key, value)
}

function removeStorage(key: string) {
  if (typeof sessionStorage === 'undefined')
    return

  sessionStorage.removeItem(key)
}

function readRole(): Role {
  const stored = readStorage(ROLE_KEY)

  if (stored && roles.includes(stored as Role))
    return stored as Role

  return 'admin'
}

export const useSessionStore = defineStore('session', {
  state: () => ({
    isLoggedIn: readStorage(AUTH_KEY) === '1',
    role: readRole(),
    displayName: readStorage(NAME_KEY) || '演示用户',
  }),
  actions: {
    login(name: string) {
      const displayName = name.trim() || '演示用户'

      this.isLoggedIn = true
      this.displayName = displayName
      writeStorage(AUTH_KEY, '1')
      writeStorage(NAME_KEY, displayName)
      writeStorage(ROLE_KEY, this.role)
    },
    setRole(role: Role) {
      this.role = role
      writeStorage(ROLE_KEY, role)
    },
    logout() {
      this.isLoggedIn = false
      this.displayName = '演示用户'
      removeStorage(AUTH_KEY)
      removeStorage(NAME_KEY)
    },
  },
})

export const sessionRoles = roles
