import { defineStore } from 'pinia'
import type { Role } from '@/types/domain'

const AUTH_KEY = 'crosserp-auth'
const ROLE_KEY = 'crosserp-role'
const NAME_KEY = 'crosserp-name'

const roles: Role[] = ['admin', 'operator', 'finance', 'viewer', 'auditor']

/**
 * 每个演示角色对应一个独立的演示用户身份。
 * 审批的「提交人 ≠ 审批人」规则按这个身份判断，所以切换角色就等于换了一个人。
 */
export const demoIdentities: Record<Role, { id: string; name: string }> = {
  admin: { id: 'demo-admin', name: '演示管理员' },
  operator: { id: 'demo-operator', name: '演示运营' },
  finance: { id: 'demo-finance', name: '演示财务' },
  viewer: { id: 'demo-viewer', name: '演示只读' },
  auditor: { id: 'demo-auditor', name: '演示审计' },
}

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

    // 登录框里输入的账号名，只用于展示；审批和审计使用角色对应的演示身份。
    loginName: readStorage(NAME_KEY) || '',
  }),
  getters: {
    userId: state => demoIdentities[state.role].id,
    displayName: state => demoIdentities[state.role].name,
  },
  actions: {
    login(name: string) {
      this.isLoggedIn = true
      this.loginName = name.trim()
      writeStorage(AUTH_KEY, '1')
      writeStorage(NAME_KEY, this.loginName)
      writeStorage(ROLE_KEY, this.role)
    },
    setRole(role: Role) {
      this.role = role
      writeStorage(ROLE_KEY, role)
    },
    logout() {
      this.isLoggedIn = false
      this.loginName = ''
      removeStorage(AUTH_KEY)
      removeStorage(NAME_KEY)
    },
  },
})

export const sessionRoles = roles