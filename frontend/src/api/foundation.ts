import { delay } from '@/api/mock-client'
import { approvalTypes, autonomyPolicies, channelPlugins, departments, documentLinks, modules, suggestions } from '@/mocks/services/foundation'
import type { AgentAutonomyPolicy, AgentSuggestion, AiModeState, ApprovalTypeDefinition, ChannelPlugin, Department, DocumentLink, ModuleSwitch } from '@/types/foundation'

// 未来: GET /api/v1/approvals/types
export async function listApprovalTypes(): Promise<ApprovalTypeDefinition[]> {
  await delay()

  return structuredClone(approvalTypes)
}

// 未来: GET /api/v1/agent/suggestions
export async function listAgentSuggestions(): Promise<AgentSuggestion[]> {
  await delay()

  return structuredClone(suggestions)
}

// 未来: GET /api/v1/agent/autonomy-policies
export async function listAutonomyPolicies(): Promise<AgentAutonomyPolicy[]> {
  await delay()

  return structuredClone(autonomyPolicies)
}

// 未来: GET /api/v1/org/departments
export async function listDepartments(): Promise<Department[]> {
  await delay()

  return structuredClone(departments)
}

// 未来: GET /api/v1/documents/links
export async function listDocumentLinks(): Promise<DocumentLink[]> {
  await delay()

  return structuredClone(documentLinks)
}

// 未来: GET /api/v1/notify/channels
export async function listChannelPlugins(): Promise<ChannelPlugin[]> {
  await delay()

  return channelPlugins
}

// 未来: GET /api/v1/admin/modules
export async function listModuleSwitches(): Promise<ModuleSwitch[]> {
  await delay()

  return structuredClone(modules)
}

// 未来: PUT /api/v1/agent/mode
export async function saveAiMode(state: AiModeState): Promise<AiModeState> {
  await delay()

  return { ...state }
}
