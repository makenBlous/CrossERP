import { readMock } from '@/api/mock-client'
import { agentDefinitions, agentRuns, chatMessages, chatThreads } from '@/mocks/agent'

export function fetchAgentDefinitions() {
  return readMock(agentDefinitions)
}

export function fetchAgentRuns() {
  return readMock(agentRuns)
}

export function fetchChat() {
  return readMock({ threads: chatThreads, messages: chatMessages })
}
