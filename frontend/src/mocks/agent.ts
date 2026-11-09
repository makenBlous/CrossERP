import type { AgentDefinition, AgentRun, ChatMessage, ChatThread } from '@/types/domain'

export const agentDefinitions: AgentDefinition[] = [
  {
    id: 'recon-explainer',
    name: '对账解释员',
    duty: '用只读工具解释异常原因，并起草待审批建议。不算钱，不写账。',
    model: 'grok-3',
    status: 'active',
    source: 'DeerFlow',
    tools: ['finance.list_issues', 'recon.get_run', 'approvals.submit_suggestion'],
    storeScope: '全部店铺',
  },
  {
    id: 'profit-analyst',
    name: '利润问答',
    duty: '按已算好的利润快照回答店铺和 SKU 问题，并给出出处。',
    model: 'grok-3',
    status: 'active',
    source: 'DeerFlow',
    tools: ['finance.get_profit', 'catalog.get_sku'],
    storeScope: 'Amazon US / UK / DE、Shopify',
  },
  {
    id: 'crm-drafter',
    name: '客户跟进草稿',
    duty: '根据客户档案起草跟进邮件。不改订单金额。',
    model: 'grok-3-mini',
    status: 'paused',
    source: 'DeerFlow',
    tools: ['crm.get_account'],
    storeScope: 'CRM 客户，不含亚马逊终端消费者',
  },
  {
    id: 'auditor-readonly',
    name: '审计只读',
    duty: '核对审计哈希链和运行记录。没有写工具。',
    model: 'grok-3',
    status: 'active',
    source: 'DeerFlow',
    tools: ['audit.list_logs', 'agent.list_runs'],
    storeScope: '只读，全公司',
  },
]

export const agentRuns: AgentRun[] = [
  { id: 'run-8841', agentName: '对账解释员', startedAt: '2026-11-09 01:12 UTC', durationMs: 4820, tokens: 2140, costUsd: 0.018, status: 'succeeded', question: '为什么 STL-US-2026-10-02 对不平？' },
  { id: 'run-8836', agentName: '利润问答', startedAt: '2026-11-08 16:40 UTC', durationMs: 2310, tokens: 980, costUsd: 0.007, status: 'succeeded', question: '10 月帐篷在美国站的利润是多少？' },
  { id: 'run-8820', agentName: '对账解释员', startedAt: '2026-11-08 09:05 UTC', durationMs: 9100, tokens: 3560, costUsd: 0.031, status: 'failed', question: '把差额直接改成平衡' },
  { id: 'run-8794', agentName: '审计只读', startedAt: '2026-11-07 22:18 UTC', durationMs: 1540, tokens: 640, costUsd: 0.004, status: 'succeeded', question: '最近一次哈希链校验结果' },
  { id: 'run-8788', agentName: '客户跟进草稿', startedAt: '2026-11-07 11:02 UTC', durationMs: 3200, tokens: 1280, costUsd: 0.006, status: 'succeeded', question: '给 Summit Trail 写一封少发货跟进' },
  { id: 'run-8771', agentName: '利润问答', startedAt: '2026-11-06 08:26 UTC', durationMs: 6100, tokens: 4020, costUsd: 0.029, status: 'running', question: '对比四店 10 月广告费占比' },
]

export const chatThreads: ChatThread[] = [
  { id: 'th-1', title: 'US 结算为什么不平', updatedAt: '2026-11-09 01:14' },
  { id: 'th-2', title: '帐篷利润出处', updatedAt: '2026-11-08 16:42' },
]

export const chatMessages: ChatMessage[] = [
  {
    id: 'm1',
    role: 'user',
    text: '结算单 STL-US-2026-10-02 为什么对不平？不要改数字。',
  },
  {
    id: 'm2',
    role: 'assistant',
    text: '我只读取系统已经算好的对账结果，没有重算金额。',
    toolCall: {
      name: 'recon.get_run',
      args: { runId: 'recon-us-10', settlementId: 'STL-US-2026-10-02' },
      summary: '只读：匹配 1,284 行，未匹配 38 行，匹配率 97.12%。汇总行与明细相差 318.55 USD。',
    },
  },
  {
    id: 'm3',
    role: 'assistant',
    text: '原因码是 SETTLEMENT_UNBALANCED。明细合计比汇总行少 318.55 USD，对应异常 iss-1022。我可以起草一张调账凭证建议，但不会直接记账。',
    toolCall: {
      name: 'finance.list_issues',
      args: { code: 'SETTLEMENT_UNBALANCED', refNo: 'STL-US-2026-10-02' },
      summary: '只读：异常 iss-1022，金额 318.55 USD，状态待处理。金额来自对账代码，不是模型生成。',
    },
  },
  {
    id: 'm4',
    role: 'assistant',
    text: '下面这张建议卡里的金额来自系统计算。提交后进入审批，批准前 write_service 不会写账。',
    suggestion: {
      title: '建议生成调账凭证',
      detail: '借：待处理财产损溢 318.55 USD；贷：平台结算清算 318.55 USD。智能体不直接记账。',
      amountLabel: '318.55 USD（来自对账结果，非模型计算）',
      status: 'draft',
    },
  },
]
