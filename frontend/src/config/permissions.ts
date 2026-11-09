import type { Role } from '@/types/domain'
import type { PermissionPoint, RolePermission, RoleTemplate } from '@/types/foundation'

/** 旧角色兼容表只保留五个历史 slug；预置模板必须走自己的权限集合。 */
export const legacyRoleMap: Partial<Record<Role, Role>> = {
  admin: 'admin',
  operator: 'operator',
  finance: 'finance',
  viewer: 'viewer',
  auditor: 'auditor',
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
  ['agent_suggestion', '智能体建议', 'Agent', 'Agent Suggestion'],

  // 补齐批次 A–E 占位页使用的 ERPNext DocType / Odoo 模型权限点。
  ['travel_request', '差旅申请', 'HR', 'Travel Request'],
  ['expense_claim_type', '费用标准', 'HR', 'Expense Claim Type'],
  ['period_closing_voucher', '期末结账', 'Accounts', 'Period Closing Voucher'],
  ['stock_ledger', '库存流水', 'Stock', 'Stock Ledger'],
  ['budget', '预算', 'Accounts', 'Budget'],
  ['exchange_rate_revaluation', '汇兑重估', 'Accounts', 'Exchange Rate Revaluation'],
  ['vat_return', 'VAT 申报', 'Accounts', 'VAT Return'],
  ['export_tax_rebate', '出口退税', 'Accounts', 'Export Tax Rebate'],
  ['contract', '合同', 'Buying', 'Contract'],
  ['supplier_scorecard', '供应商评估', 'Buying', 'Supplier Scorecard'],
  ['batch', '批次', 'Stock', 'Batch'],
  ['stock_reconciliation', '库存盘点', 'Stock', 'Stock Reconciliation'],
  ['audit_log', '审计日志', 'Platform', 'Audit Log'],
  ['attendance', '考勤', 'HR', 'Attendance'],
  ['salary_structure', '薪资规则', 'Payroll', 'Salary Structure'],
  ['employee_tax_exemption_declaration', '专项附加扣除', 'Payroll', 'Employee Tax Exemption Declaration'],
  ['office_supply', '办公用品', 'Stock', 'Office Supply'],
  ['item', '商品', 'Stock', 'Item'],
  ['item_group', '商品类目', 'Stock', 'Item Group'],
  ['brand', '品牌', 'Stock', 'Brand'],
  ['listing', '平台 Listing', 'Selling', 'Item Price'],
  ['warehouse', '仓库', 'Stock', 'Warehouse'],
  ['shipment', '物流运单', 'Stock', 'Shipment'],
  ['advertisement', '广告活动', 'Selling', 'Campaign'],
  ['customer', '客户', 'Selling', 'Customer'],
  ['lead', '销售线索', 'Selling', 'Lead'],
  ['contact', '联系人', 'Selling', 'Contact'],
  ['ticket', '售后工单', 'Support', 'Issue'],
  ['user', '用户账号', 'Identity', 'User'],
  ['user_admin', '用户管理', 'Identity', 'User'],
  ['system', '系统', 'Platform', 'System Settings'],
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

const fieldPermissionPoints: PermissionPoint[] = [
  { key: 'sku.cost:read', labelZh: 'SKU 成本字段查看', labelEn: 'SKU Cost Field Read', module: 'Accounts', kind: 'field', sensitive: true, dataScopeRuleTypes: ['all', 'store', 'owner'], erpnextRef: 'Item valuation_rate', odooRef: 'product.template.standard_price' },
  { key: 'sku.margin:read', labelZh: 'SKU 毛利字段查看', labelEn: 'SKU Margin Field Read', module: 'Accounts', kind: 'field', sensitive: true, dataScopeRuleTypes: ['all', 'store', 'owner'], erpnextRef: 'Item margin', odooRef: 'product.template.margin' },
  { key: 'employee.salary:read', labelZh: '员工薪资字段查看', labelEn: 'Employee Salary Field Read', module: 'Payroll', kind: 'field', sensitive: true, dataScopeRuleTypes: ['all', 'self'], erpnextRef: 'Employee.salary', odooRef: 'hr.employee.wage' },
  { key: 'employee.id_number:read', labelZh: '员工证件字段查看', labelEn: 'Employee ID Number Field Read', module: 'HR', kind: 'field', sensitive: true, dataScopeRuleTypes: ['all', 'self'], erpnextRef: 'Employee.id_number', odooRef: 'hr.employee.identification_id' },
  { key: 'employee.bank_account:read', labelZh: '员工银行账号字段查看', labelEn: 'Employee Bank Account Field Read', module: 'HR', kind: 'field', sensitive: true, dataScopeRuleTypes: ['all', 'self'], erpnextRef: 'Employee.bank_account', odooRef: 'hr.employee.bank_account' },
  { key: 'buyer.contact:read', labelZh: '买家联系方式字段查看', labelEn: 'Buyer Contact Field Read', module: 'Selling', kind: 'field', sensitive: true, dataScopeRuleTypes: ['all', 'store', 'owner'], erpnextRef: 'Customer.contact', odooRef: 'res.partner.phone' },
  { key: 'salary_slip:read_own', labelZh: '本人工资条查看', labelEn: 'Own Salary Slip Read', module: 'Payroll', kind: 'menu', sensitive: true, dataScopeRuleTypes: ['self'], erpnextRef: 'Salary Slip', odooRef: 'hr.payslip' },
  { key: 'salary_slip:read_all', labelZh: '全部工资条查看', labelEn: 'All Salary Slips Read', module: 'Payroll', kind: 'menu', sensitive: true, dataScopeRuleTypes: ['all', 'department'], erpnextRef: 'Salary Slip', odooRef: 'hr.payslip' },
  { key: 'employee_record:read_own', labelZh: '本人档案查看', labelEn: 'Own Employee Record Read', module: 'HR', kind: 'menu', dataScopeRuleTypes: ['self'], erpnextRef: 'Employee', odooRef: 'hr.employee' },
]

permissionCatalog.push(...fieldPermissionPoints)

// ---- 补齐批次 D：页面动作权限点（薪资字段默认收窄） ----
export const gapDPermissionPoints: PermissionPoint[] = [
  { key: 'agent_autonomy:write', labelZh: '修改自主等级', labelEn: 'Edit autonomy policy', module: 'Agent', kind: 'action', sensitive: true, dataScopeRuleTypes: ['all'] },
  { key: 'agent_mode:write', labelZh: '切换 AI 总开关', labelEn: 'Change AI mode', module: 'Agent', kind: 'action', sensitive: true, dataScopeRuleTypes: ['all'] },
  { key: 'payroll_run:calculate', labelZh: '发起算薪', labelEn: 'Calculate payroll', module: 'Payroll', kind: 'action', sensitive: true, dataScopeRuleTypes: ['all', 'department'] },
  { key: 'salary_slip:read_own', labelZh: '查看本人工资条', labelEn: 'Read own payslip', module: 'Payroll', kind: 'field', sensitive: true, dataScopeRuleTypes: ['self'] },
  { key: 'salary_slip:read_all', labelZh: '查看全部工资字段', labelEn: 'Read all salary fields', module: 'Payroll', kind: 'field', sensitive: true, dataScopeRuleTypes: ['all'] },
]

permissionCatalog.push(...gapDPermissionPoints)

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

const templatePermissions: Record<string, string[]> = {
  owner_manager: permissionCatalog.map(point => point.key),
  store_operator: ['item:read', 'item:write', 'item:create', 'item_group:read', 'brand:read', 'listing:read', 'sales_order:read', 'delivery_note:read', 'report:read', 'stock_ledger:read', 'material_request:read', 'approval:read', 'notification:read', 'customer:read', 'lead:read', 'contact:read', 'ticket:read', 'document:read'],
  operations_manager: ['approval:read', 'approval:approve', 'report:read', 'budget:read', 'notification:read'],
  advertising: ['advertisement:read', 'advertisement:write', 'advertisement:create', 'advertisement:import', 'sales_order:read', 'listing:read', 'report:read', 'notification:read'],
  product_developer: ['item:read', 'item:write', 'item:create', 'item_group:read', 'item_group:write', 'brand:read', 'brand:write', 'listing:read', 'supplier:read', 'request_for_quotation:read', 'request_for_quotation:create', 'report:read', 'notification:read'],
  purchaser: ['supplier:read', 'supplier:write', 'supplier:create', 'purchase_order:read', 'purchase_order:write', 'purchase_order:create', 'purchase_receipt:read', 'purchase_receipt:submit', 'request_for_quotation:read', 'request_for_quotation:write', 'request_for_quotation:create', 'supplier_quotation:read', 'contract:read', 'material_request:read', 'report:read', 'approval:read', 'notification:read'],
  warehouse_logistics: ['warehouse:read', 'warehouse:write', 'warehouse:create', 'stock_ledger:read', 'stock_entry:read', 'stock_entry:write', 'stock_entry:create', 'purchase_receipt:read', 'purchase_receipt:submit', 'delivery_note:read', 'delivery_note:submit', 'batch:read', 'stock_reconciliation:read', 'shipment:read', 'shipment:write', 'shipment:create', 'notification:read'],
  customer_service: ['customer:read', 'contact:read', 'ticket:read', 'ticket:write', 'ticket:create', 'sales_order:read', 'delivery_note:read', 'report:read', 'notification:read'],
  accountant: ['journal_entry:read', 'journal_entry:write', 'journal_entry:create', 'payment_entry:read', 'expense_claim:read', 'employee_advance:read', 'report:read', 'stock_ledger:read', 'budget:read', 'audit_log:read', 'approval:read', 'notification:read', 'integration:read'],
  finance_manager: ['approval:read', 'approval:write', 'approval:approve', 'report:read', 'report:write', 'journal_entry:read', 'journal_entry:write', 'journal_entry:create', 'journal_entry:approve', 'payment_entry:read', 'payment_entry:write', 'payment_entry:approve', 'expense_claim:read', 'budget:read', 'budget:write', 'period_closing_voucher:approve', 'integration:write', 'audit_log:read', 'notification:read'],
  cashier: ['payment_entry:read', 'payment_entry:write', 'payment_entry:submit', 'journal_entry:read', 'report:read', 'approval:read', 'notification:read'],
  hr_admin: ['employee_record:read', 'employee_record:read_own', 'employee_record:write', 'employee_record:create', 'employee.salary:read', 'employee.id_number:read', 'salary_slip:read', 'salary_slip:read_own', 'salary_slip:read_all', 'salary_slip:write', 'salary_slip:create', 'payroll_run:calculate', 'attendance:read', 'attendance:write', 'leave_application:read', 'leave_application:write', 'leave_application:approve', 'contract:read', 'contract:write', 'asset:read', 'asset:write', 'notification:read', 'notification:write', 'document:read', 'approval:read'],
  employee: ['expense_claim:read', 'expense_claim:create', 'expense_claim:write', 'employee_advance:read', 'employee_advance:create', 'travel_request:read', 'travel_request:create', 'leave_application:read', 'leave_application:create', 'salary_slip:read_own', 'employee_record:read_own', 'notification:read', 'document:read', 'office_supply:read', 'office_supply:create', 'approval:read'],
  department_manager: ['approval:read', 'approval:approve', 'expense_claim:read', 'leave_application:read', 'leave_application:approve', 'purchase_order:read', 'sales_order:read', 'employee_record:read', 'budget:read', 'notification:read'],

  // 审计可以只读查看权限配置，便于核对改前改后；没有任何 permission:write/approve。
  auditor_template: ['report:read', 'audit_log:read', 'audit_log:export', 'agent_tool:read', 'permission:read'],
  external_viewer: ['report:read', 'notification:read'],
}

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
  permissions: [
    { permissionKey: 'user:read', effect: 'allow' as const, source: `模板 ${nameZh}` },
    { permissionKey: 'user:write', effect: 'allow' as const, source: `模板 ${nameZh}` },
    ...(templatePermissions[id] ?? []).map(permissionKey => ({ permissionKey, effect: 'allow' as const, source: `模板 ${nameZh}` })),
    ...extra,
  ],
  defaultDataScopes,
  fieldRestrictions: ['employee', 'department_manager', 'external_viewer', 'store_operator', 'operations_manager', 'advertising', 'product_developer', 'purchaser', 'warehouse_logistics', 'customer_service'].includes(id)
    ? { cost: 'hidden', margin: 'hidden', salary: 'hidden', salaryDetail: 'hidden', idCard: 'hidden', bankAccount: 'hidden', buyerContact: 'masked' }
    : id === 'hr_admin'
      ? { salary: 'visible', salaryDetail: 'visible', idCard: 'visible', bankAccount: 'visible' }
      : id === 'auditor_template'
        ? { salary: 'masked', salaryDetail: 'hidden', bankAccount: 'hidden', idCard: 'masked' }
        : {},
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
  template('department_manager', '部门主管', 'Department Manager', ['employee'], undefined, ['department'], ['HR Manager'], ['hr.group_hr_manager'], [{ permissionKey: 'employee_record:read', effect: 'allow', dataScopes: ['department'], source: '模板 部门主管（本部门）' }]),
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
