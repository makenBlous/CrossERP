export type ChatRole = 'user' | 'assistant'

export interface ChatCard {
  kind: string
  title: string
  lines: Array<{ label: string; value: string }>
  draft?: unknown
}

export interface ChatSuggestion {
  id: string
  label: string
  prompt: string
  icon?: string
}

export interface ChatDisplayMessage {
  id: string
  role: ChatRole
  text: string
  time?: string
  toolCall?: {
    name: string
    summary: string
  }
  card?: ChatCard
  submitted?: boolean
}

export type ChatState = 'idle' | 'loading' | 'error' | 'cancelled'
