import type { Role } from '@/types/domain'
import type { PermissionPoint, RolePermission, RoleTemplate } from '@/types/foundation'

export const legacyRoleMap: Record<Role, Role> = {
  admin: 'admin',
  operator: 'operator',
  finance: 'finance',
  viewer: 'viewer',
  auditor: 'auditor',
  owner_manager: 'admin',
  operations_manager: 'operator',
  store_operator: 'operator',
  advertising: 'operator',
  product_developer: 'operator',
  purchaser: 'operator',
  warehouse_logistics: 'operator',
  customer_service: 'operator',
  accountant: 'finance',
  finance_manager: 'finance',
  cashier: 'finance',
  hr_admin: 'admin',
  employee: 'operator',
  department_manager: 'operator',
  auditor_template: 'auditor',
  external_viewer: 'viewer',
}

const legacyActionLabels: Record<string, [string, string]> = {
  read: ['查看', 'Read'],
  write: ['修改', 'Write'],
  create: ['新建', 'Create'],
  delete: ['删除', 'Delete'],
  submit: ['提交', 'Submit'],
  cancel: ['作废', 'Cancel'],
  amend: ['修订', 'Amend'],
  print: ['打印', 'Print'],
  email: ['邮件', 'Email'],
  export: ['导出', 'Export'],
  import: ['导入', 'Import'],
  report: ['报表', 'Report'],
  share: ['分享', 'Share'],
  approve: ['审批', 'Approve'],
}

const docTypes: Array<[string, string, string, string]> = [
  ['sales_order', '销售订单', 'Selling', 'Sales Order'],
  ['purchase_order', '采购订单', 'Buying', 'Purchase Order'],
  ['purchase_receipt', '采购收货', 'Buying', 'Purchase Receipt'],
  ['delivery_note', '出库单', 'Stock', 'Delivery Note'],
  ['stock_entry', '库存调拨', 'Stock', 'Stock Entry'],
  ['material_request', '物料需求', 'Buying', 'Material Request'],
  ['request_for_quotation', '询价单', 'Buying', 'Request for Quotation'],
  ['supplier_quotation', '供应商报价', 'Buying', 'Supplier Quotation'],
  ['journal_entry', '会计凭证', 'Accounts', 'Journal Entry'],
  ['payment_entry', '收付款', 'Accounts', 'Payment Entry'],
  ['expense_claim', '费用报销', 'HR', 'Expense Claim'],
  ['employee_advance', '员工借款', 'HR', 'Employee Advance'],
  ['salary_slip', '工资条', 'Payroll', 'Salary Slip'],
  ['leave_application', '请假申请', 'HR', 'Leave Application'],
  ['asset', '固定资产', 'Assets', 'Asset'],
  ['supplier', '供应商', 'Buying', 'Supplier'],
  ['approval', '审批单', 'Workflow', 'Workflow'],
  ['notification', '通知', 'Platform', 'Notification'],
  ['report', '报表', 'Accounts', 'Report'],
  ['integration', '集成', 'Integrations', 'Integration'],
  ['agent_tool', '智能体工具', 'Agent', 'Agent Tool'],
  ['document', '知识文档', 'Knowledge', 'Document'],
  ['employee_record', '员工档案', 'HR', 'Employee'],
  ['permission', '权限', 'Identity', 'Role Permission'],
]

export const permissionCatalog: PermissionPoint[] = docTypes.flatMap(([docType, label, module, erpnextRef]) =>
  Object.entries(legacyActionLabels).map(([action, [labelZh, labelEn]]) => ({
    key: `${docType}:${action}`,
    labelZh: `${label}${labelZh}`,
    labelEn: `${erpnextRef} ${labelEn}`,
    module,
    kind: action === 'read' ? 'menu' : 'action',
    sensitive: ['salary_slip', 'payment_entry', 'permission'].includes(docType),
    dataScopeRuleTypes: ['all', 'store', 'department', 'self', 'owner', 'warehouse', 'amount'],
    erpnextRef,
    odooRef: docType === 'expense_claim' ? 'hr_expense' : docType === 'journal_entry' ? 'account.move' : `x_${docType}`,
  })),
)

export const legacyPermissionKeys: Record<string, string> = {
  view: 'system:read',
  create: 'system:create',
  update: 'system:write',
  delete: 'system:delete',
  approve: 'approval:approve',
  export: 'system:export',
  ship: 'delivery_note:submit',
  receive: 'purchase_receipt:submit',
  suggest: 'agent_suggestion:create',
}

export const legacyRoleActions: Record<'admin' | 'operator' | 'finance' | 'viewer' | 'auditor', string[]> = {
  admin: ['view', 'create', 'update', 'delete', 'approve', 'export', 'ship', 'receive', 'suggest'],
  operator: ['view', 'create', 'update', 'export', 'ship', 'receive', 'suggest'],
  finance: ['view', 'approve', 'export', 'suggest'],
  viewer: ['view'],
  auditor: ['view', 'export'],
}

const basePermissions = (role: 'admin' | 'operator' | 'finance' | 'viewer' | 'auditor'): RolePermission[] => [
  ...legacyRoleActions[role].map(action => ({ permissionKey: legacyPermissionKeys[action], effect: 'allow' as const, source: `旧角色 ${role}` })),
  ...permissionCatalog.filter(point => point.key.endsWith(':read')).map(point => ({ permissionKey: point.key, effect: 'allow' as const, source: `模板 ${role}` })),
]

const isLegacyRole = (role: Role): role is 'admin' | 'operator' | 'finance' | 'viewer' | 'auditor' => ['admin', 'operator', 'finance', 'viewer', 'auditor'].includes(role)

const template = (
  id: string,
  nameZh: string,
  nameEn: string,
  parentIds: string[],
  legacyRole: Role | undefined,
  defaultDataScopes: RoleTemplate['defaultDataScopes'],
  erpnextRefs: string[],
  odooRefs: string[],
  extra: RolePermission[] = [],
): RoleTemplate => ({
  id,
  nameZh,
  nameEn,
  parentIds,
  legacyRole,
  permissions: [...(legacyRole && isLegacyRole(legacyRole) ? basePermissions(legacyRole) : basePermissions('viewer')), ...extra],
  defaultDataScopes,
  fieldRestrictions: {},
  erpnextRefs,
  odooRefs,
})

export const roleTemplates: RoleTemplate[] = [
  template('owner_manager', '老板/总经理', 'Owner / General Manager', [], 'admin', ['all'], ['System Manager'], ['base.group_system']),
  template('store_operator', '店铺运营', 'Store Operator', [], 'operator', ['store', 'owner'], ['Sales User'], ['sales_team.group_sale_salesman']),
  template('operations_manager', '运营主管', 'Operations Manager', ['store_operator'], undefined, ['store', 'department'], ['Sales Manager'], ['sales_team.group_sale_manager']),
  template('advertising', '广告投放', 'Advertising', [], undefined, ['store', 'owner'], ['Sales User'], ['marketing.group_marketing_user']),
  template('product_developer', '产品开发/选品', 'Product Development', [], undefined, ['owner'], ['Item Manager'], ['product.group_product_manager']),
  template('purchaser', '采购', 'Purchaser', [], 'operator', ['owner', 'warehouse'], ['Purchase User'], ['purchase.group_purchase_user']),
  template('warehouse_logistics', '仓储/物流', 'Warehouse / Logistics', [], undefined, ['warehouse'], ['Stock User'], ['stock.group_stock_user']),
  template('customer_service', '客服/售后', 'Customer Service', [], undefined, ['store', 'owner'], ['Support User'], ['helpdesk.group_helpdesk_user']),
  template('accountant', '会计', 'Accountant', [], 'finance', ['all'], ['Accounts User'], ['account.group_account_user']),
  template('finance_manager', '财务主管', 'Finance Manager', ['accountant'], 'finance', ['all'], ['Accounts Manager'], ['account.group_account_manager']),
  template('cashier', '出纳', 'Cashier', [], undefined, ['owner'], ['Accounts User'], ['account.group_account_user']),
  template('hr_admin', '人事行政', 'HR & Administration', [], 'admin', ['all'], ['HR User', 'Payroll User'], ['hr.group_hr_user']),
  template('employee', '普通员工', 'Employee', [], 'operator', ['self'], ['Employee'], ['base.group_user']),
  template('department_manager', '部门主管', 'Department Manager', ['employee'], undefined, ['department'], ['HR Manager'], ['hr.group_hr_manager']),
  template('auditor_template', '审计', 'Auditor', [], 'auditor', ['all'], ['System Manager'], ['base.group_system']),
  template('external_viewer', '只读/外部顾问', 'Read-only / External Advisor', [], 'viewer', ['store'], ['Employee'], ['base.group_user']),
]

export const moduleRegistry = [
  { id: 'hr', nameZh: '人事', nameEn: 'HR', enabled: false, defaultPhase: 'later' as const },
  { id: 'office', nameZh: '行政', nameEn: 'Administration', enabled: false, defaultPhase: 'later' as const },
  { id: 'integrations', nameZh: '集成', nameEn: 'Integrations', enabled: true, defaultPhase: 'now' as const },
  { id: 'knowledge', nameZh: '知识库', nameEn: 'Knowledge', enabled: true, defaultPhase: 'now' as const },
  { id: 'collaboration', nameZh: '协作', nameEn: 'Collaboration', enabled: true, defaultPhase: 'now' as const },
  { id: 'expense', nameZh: '费用', nameEn: 'Expenses', enabled: true, defaultPhase: 'now' as const },
] as const
