export type { AgentAdapter, AgentCard, AgentPageContext, AgentPart } from '@/agent/adapter'
export { createAgentAdapter, MockAgentAdapter } from '@/agent/mock-adapter'

/**
 * 换成 DeerFlow 时：
 * 1. 新建 DeerFlowAdapter，实现 AgentAdapter.sendMessage。
 * 2. 把 createAgentAdapter() 的返回值改成 DeerFlowAdapter。
 * 3. 不要在适配器里计算金额。数字只来自 CrossERP 只读接口。
 * 4. 写操作只调用 submitAgentSuggestion，生成待审批记录。
 */
