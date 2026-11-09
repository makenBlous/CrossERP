/**
 * 报销凭证的示例科目映射。
 *
 * 依据：Frappe HR Expense Claim 文档（https://docs.frappe.io/hr/expense-claim）
 * 其说明提交报销时借记费用科目、贷记员工应付科目，付款时再借记员工应付、
 * 贷记银行。以下中国科目名称属于推断，待会计核实，不代表合规会计政策。
 */
export interface ExpenseAccountMapping {
  category: string
  debitAccount: string
  creditAccount: '其他应付款-员工'
  note: string
}

export const EXPENSE_ACCOUNT_MAPPINGS: readonly ExpenseAccountMapping[] = [
  { category: '交通', debitAccount: '管理费用-差旅费', creditAccount: '其他应付款-员工', note: '示例映射，待会计核实；科目名称推断，待会计核实' },
  { category: '住宿', debitAccount: '管理费用-差旅费', creditAccount: '其他应付款-员工', note: '示例映射，待会计核实；科目名称推断，待会计核实' },
  { category: '餐补', debitAccount: '管理费用-业务招待费', creditAccount: '其他应付款-员工', note: '示例映射，待会计核实；科目名称推断，待会计核实' },
  { category: '广告', debitAccount: '销售费用-广告费', creditAccount: '其他应付款-员工', note: '示例映射，待会计核实；科目名称推断，待会计核实' },
  { category: '销售', debitAccount: '销售费用-销售费用', creditAccount: '其他应付款-员工', note: '示例映射，待会计核实；科目名称推断，待会计核实' },
  { category: '推广', debitAccount: '销售费用-推广费', creditAccount: '其他应付款-员工', note: '示例映射，待会计核实；科目名称推断，待会计核实' },
  { category: '佣金', debitAccount: '销售费用-佣金', creditAccount: '其他应付款-员工', note: '示例映射，待会计核实；科目名称推断，待会计核实' },
  { category: '其他', debitAccount: '管理费用-其他', creditAccount: '其他应付款-员工', note: '示例映射，待会计核实；科目名称推断，待会计核实' },
]

export function expenseAccountMappingForCategory(category: string): ExpenseAccountMapping {
  const exact = EXPENSE_ACCOUNT_MAPPINGS.find(item => item.category === category)
  if (exact)
    return exact

  const keyword = EXPENSE_ACCOUNT_MAPPINGS.find(item => item.category !== '其他' && category.includes(item.category))

  return keyword ?? EXPENSE_ACCOUNT_MAPPINGS[EXPENSE_ACCOUNT_MAPPINGS.length - 1]
}
