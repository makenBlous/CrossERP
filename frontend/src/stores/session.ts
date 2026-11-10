import { defineStore } from 'pinia'
import type { Role } from '@/types/domain'
import { roleTemplates } from '@/config/permissions'

const AUTH_KEY = 'crosserp-auth'
const ROLE_KEY = 'crosserp-role'
const NAME_KEY = 'crosserp-name'

const legacyRoles: Role[] = ['admin', 'operator', 'finance', 'viewer', 'auditor']
const roles: Role[] = [...legacyRoles, ...roleTemplates.map(item => item.id as Role)]

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
  owner_manager: { id: 'demo-owner-manager', name: '演示老板/总经理' },
  operations_manager: { id: 'demo-operations-manager', name: '演示运营主管' },
  store_operator: { id: 'demo-store-operator', name: '演示店铺运营' },
  advertising: { id: 'demo-advertising', name: '演示广告投放' },
  product_developer: { id: 'demo-product-developer', name: '演示产品开发/选品' },
  purchaser: { id: 'demo-purchaser', name: '演示采购' },
  warehouse_logistics: { id: 'demo-warehouse-logistics', name: '演示仓储/物流' },
  customer_service: { id: 'demo-customer-service', name: '演示客服/售后' },
  accountant: { id: 'demo-accountant', name: '演示会计' },
  finance_manager: { id: 'demo-finance-manager', name: '演示财务主管' },
  cashier: { id: 'demo-cashier', name: '演示出纳' },
  hr_admin: { id: 'demo-hr-admin', name: '演示人事行政' },
  employee: { id: 'demo-employee', name: '演示普通员工' },
  department_manager: { id: 'demo-ops-manager', name: '演示运营主管' },
  auditor_template: { id: 'demo-auditor-template', name: '演示审计' },
  external_viewer: { id: 'demo-external-viewer', name: '演示只读/外部顾问' },
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

function readBaseUrl() {
  const baseUrl = import.meta.env?.BASE_URL

  return typeof baseUrl === 'string' && baseUrl.length > 0 ? baseUrl : '/'
}

/** 登录页地址。跟随 Vite base，子路径部署时不能写死根路径。 */
export function loginPageHref() {
  const base = readBaseUrl()

  return `${base.endsWith('/') ? base : `${base}/`}login`
}

function replaceWithLoginPage() {
  if (typeof window === 'undefined')
    return

  window.location.replace(loginPageHref())
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
      replaceWithLoginPage()
    },
  },
})

export const sessionRoles = roles
