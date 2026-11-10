import { assertPermission, database, delay } from '@/api/mock-client'
import { projectAgentDefinitions, projectAgentRuns, projectChat } from '@/mocks/project'

// 未来: GET /api/v1/agent/definitions
export async function fetchAgentDefinitions() {
  await delay()
  assertPermission('agent_tool:read')

  return projectAgentDefinitions(database().db)
}

// 未来: GET /api/v1/agent/runs
export async function fetchAgentRuns() {
  await delay()
  assertPermission('agent_tool:read')

  return projectAgentRuns(database().db)
}

// 未来: GET /api/v1/agent/threads
export async function fetchChat() {
  await delay()
  assertPermission('agent_tool:read')

  return projectChat(database().db)
}
