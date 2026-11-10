import type { CurrencyCode, Role } from '@/types/domain'

export type LeadStage = 'new' | 'qualified' | 'proposal' | 'converted'
export interface CrmLead { id: string; name: string; company: string; email: string; source: string; owner: string; stage: LeadStage; accountId: string | null; contactId: string | null; opportunityId: string | null; createdAt: string }
export interface CrmActivity { id: string; subject: string; kind: '电话' | '邮件' | '会议'; at: string; accountId: string | null; owner: string; status: 'planned' | 'done' }
export interface CrmReview { id: string; source: string; author: string; rating: number; title: string; content: string; sku: string; status: 'pending' | 'published' }
export interface CrmTicketMessage { id: string; ticketId: string; author: string; text: string; at: string; internal: boolean }
export interface RoleOverride { role: Role; hiddenGroups: string[]; hiddenPageIds: string[] }
export interface AdminIntegration { id: string; name: string; platform: string; status: 'connected' | 'needs_attention' | 'disabled'; account: string; lastSync: string }
export interface AdminModule { id: string; name: string; description: string; enabled: boolean }
export interface AdminDictionary { id: string; group: string; code: string; label: string; active: boolean }
export interface AdminNotification { id: string; channel: string; event: string; enabled: boolean; target: string }
export interface AdminSetting { id: string; key: string; label: string; value: string | boolean; description: string }
export interface AccountToken { id: string; name: string; prefix: string; createdAt: string; lastUsedAt: string | null; revoked: boolean; ownerUserId: string }
export interface AccountSession { id: string; device: string; location: string; ip: string; lastSeenAt: string; current: boolean }

export interface CrmOpportunityView { id: string; accountId: string; name: string; amount: number; currency: CurrencyCode; stage: string; accountName: string }
