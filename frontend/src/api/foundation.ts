import { assertPermission, delay } from '@/api/mock-client'
import { approvalTypes, autonomyPolicies, channelPlugins, departments, documentLinks, modules, suggestions } from '@/mocks/services/foundation'
import type { AgentAutonomyPolicy, AgentSuggestion, AiModeState, ApprovalTypeDefinition, ChannelPlugin, Department, DocumentLink, ModuleSwitch } from '@/types/foundation'
import { updateAutonomyPolicy } from '@/utils/autonomy'

// 未来: GET /api/v1/approvals/types
export async function listApprovalTypes(): Promise<ApprovalTypeDefinition[]> {
  await delay()
  assertPermission('approval:read')

  return structuredClone(approvalTypes)
}

// 未来: GET /api/v1/agent/suggestions
export async function listAgentSuggestions(): Promise<AgentSuggestion[]> {
  await delay()
  assertPermission('agent_suggestion:read')

  return structuredClone(suggestions)
}

// 未来: GET /api/v1/agent/autonomy-policies
export async function listAutonomyPolicies(): Promise<AgentAutonomyPolicy[]> {
  await delay()
  assertPermission('agent_tool:read')

  return structuredClone(autonomyPolicies)
}

// 未来: PUT /api/v1/agent/autonomy-policies/{id}
export async function saveAutonomyPolicy(policy: AgentAutonomyPolicy, level: AgentAutonomyPolicy['level']): Promise<AgentAutonomyPolicy> {
  await delay()
  assertPermission('agent_tool:write')

  return updateAutonomyPolicy(policy, level)
}

// 未来: GET /api/v1/org/departments
export async function listDepartments(): Promise<Department[]> {
  await delay()
  assertPermission('employee_record:read')

  return structuredClone(departments)
}

// 未来: GET /api/v1/documents/links
export async function listDocumentLinks(): Promise<DocumentLink[]> {
  await delay()
  assertPermission('document:read')

  return structuredClone(documentLinks)
}

// 未来: GET /api/v1/notify/channels
export async function listChannelPlugins(): Promise<ChannelPlugin[]> {
  await delay()
  assertPermission('notification:read')

  return channelPlugins
}

// 未来: GET /api/v1/admin/modules
export async function listModuleSwitches(): Promise<ModuleSwitch[]> {
  await delay()
  assertPermission('permission:read')

  return structuredClone(modules)
}

// 未来: PUT /api/v1/agent/mode
export async function saveAiMode(state: AiModeState): Promise<AiModeState> {
  await delay()
  assertPermission('agent_tool:write')

  return { ...state }
}
