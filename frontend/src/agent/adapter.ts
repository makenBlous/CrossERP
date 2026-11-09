import type { SuggestionDraft } from '@/api/workflows'

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
