import type { AgentAutonomyPolicy, AgentSuggestion, ApprovalTypeDefinition, Department, DocumentLink } from '@/types/foundation'

export const approvalTypes: ApprovalTypeDefinition[] = [
  {
    id: 'approval-expense-claim',
    code: 'expense_claim',
    nameZh: '费用报销',
    nameEn: 'Expense Claim',
    docType: 'Expense Claim',
    docStatus: 0,
    businessStatus: 'draft',
    defaultImApprovalEnabled: true,
    imAmountThreshold: 50000,
    rules: [
      { id: 'expense-l1', level: 1, approverType: 'department_manager', approverRef: 'department_manager', maxAmount: 3000, imApprovalEnabled: true, imApprovalMaxAmount: 3000, imChannelIds: ['feishu', 'wecom'] },
      { id: 'expense-l2', level: 2, approverType: 'role', approverRef: 'finance_manager', minAmount: 3000, imApprovalEnabled: true, imApprovalMaxAmount: 50000, imChannelIds: ['feishu', 'wecom'] },
    ],
  },
  {
    id: 'approval-payment-entry',
    code: 'payment_entry',
    nameZh: '付款申请',
    nameEn: 'Payment Entry',
    docType: 'Payment Entry',
    docStatus: 0,
    businessStatus: 'draft',
    defaultImApprovalEnabled: true,
    imAmountThreshold: 50000,
    rules: [{ id: 'payment-l1', level: 1, approverType: 'role', approverRef: 'finance_manager', imApprovalEnabled: true, imApprovalMaxAmount: 50000, imChannelIds: ['feishu', 'wecom'] }],
  },
  {
    id: 'approval-journal-entry',
    code: 'journal_entry',
    nameZh: '会计凭证',
    nameEn: 'Journal Entry',
    docType: 'Journal Entry',
    docStatus: 0,
    businessStatus: 'draft',
    defaultImApprovalEnabled: false,
    rules: [{ id: 'journal-l1', level: 1, approverType: 'role', approverRef: 'finance_manager', imApprovalEnabled: false, imChannelIds: [] }],
  },
]

export const suggestions: AgentSuggestion[] = [
  {
    id: 'sug-001',
    title: '补货建议',
    summary: 'SKU CN-1001 的可售天数低于安全阈值。',
    origin: 'agent',
    agentSuggestionId: 'run-001',
    onBehalfOfUserId: 'demo-operator',
    level: 'L2',
    confidence: 'high',
    evidence: [{ label: '库存余额', href: '/inventory/on-hand', recordId: 'bal-001' }],
    status: 'open',
    expiresAt: '2026-11-17T00:00:00Z',
    docType: 'Material Request',
  },
]

export const autonomyPolicies: AgentAutonomyPolicy[] = [
  { id: 'policy-tag-issue', moduleCode: 'issues', action: 'tag_issue', roleId: '*', level: 'L3', sideEffect: 'execute_l3', dailyLimit: 200, usedToday: 3, whitelist: true, hardMaxLevel: 'L3', reason: '白名单低风险动作，可撤销且不涉及金额' },
  { id: 'policy-remind-missing-receipt', moduleCode: 'expense', action: 'remind_missing_receipt', roleId: '*', level: 'L3', sideEffect: 'execute_l3', dailyLimit: 200, usedToday: 1, whitelist: true, hardMaxLevel: 'L3', reason: '内部提醒白名单动作' },
  { id: 'policy-draft-voucher', moduleCode: 'finance', action: 'draft_voucher', roleId: '*', level: 'L2', sideEffect: 'propose', dailyLimit: 50, usedToday: 0, whitelist: false, hardMaxLevel: 'L2', reason: '涉及凭证，硬上限 L2' },
]

export const documentLinks: DocumentLink[] = [
  { id: 'link-001', fromDocType: 'Sales Order', fromDocId: 'ord-1001', toDocType: 'Purchase Order', toDocId: 'po-1001', relation: 'derived', label: '补货来源' },
]

export const departments: Department[] = [
  { id: 'dept-ops', code: 'OPS', name: '运营部', parentId: null, managerUserId: 'demo-operator', active: true },
  { id: 'dept-fin', code: 'FIN', name: '财务部', parentId: null, managerUserId: 'demo-finance', active: true },
]
