// Vuexy 的 apps/chat 只渲染消息，没有只读查询/待审批建议的适配器。页面不直接调模型。
import type { SuggestionDraft } from '@/api/workflows'
import type { AgentAutonomyLevel, AgentCardEvidence } from '@/types/foundation'

export interface AgentPageContext {
  pageName: string
  route: string
  selectedId: string | null
  locale: 'zh-CN' | 'en'
}

export interface AgentCardLine {
  label: string
  value: string
}

export interface AgentCard {
  kind: 'query' | 'suggestion'
  title: string
  lines: AgentCardLine[]
  draft?: SuggestionDraft
  level?: AgentAutonomyLevel
  confidence?: 'high' | 'medium' | 'low'
  evidence?: AgentCardEvidence[]
  suggestionId?: string
  expiresAt?: string
}

export interface AgentPart {
  kind: 'text' | 'card'
  text?: string
  card?: AgentCard
}

export interface AgentAdapter {
  sendMessage(
    context: AgentPageContext,
    message: string,
    emit: (part: AgentPart) => void,
  ): Promise<void>
}
