import type { Role } from '@/types/domain'

export type KbDocStatus = 'draft' | 'in_review' | 'published' | 'archived'
export type KbDocKind = 'policy' | 'sop' | 'help' | 'qa' | 'ticket_lesson' | 'contract' | 'id_copy' | 'certificate'

export interface KbSpace {
  id: string
  name: string
  description: string
  memberCount: number
  financeOnly: boolean
  updatedAt: string
}

export interface KbVersion {
  id: string
  docId: string
  version: number
  content: string
  author: string
  createdAt: string
  status: KbDocStatus
}

export interface KbDocument {
  id: string
  spaceId: string
  title: string
  content: string
  kind: KbDocKind
  status: KbDocStatus
  tags: string[]
  sensitive: boolean
  expiresOn: string | null
  owner: string
  currentVersion: number
  versions: KbVersion[]
  sourceRef?: string
  updatedAt: string
}

export interface KbReviewItem {
  id: string
  type: 'document' | 'qa'
  targetId: string
  title: string
  summary: string
  submittedBy: string
  submittedAt: string
  status: 'pending' | 'approved' | 'rejected'
  reason?: string
}

export interface KbQaItem {
  id: string
  question: string
  answer: string
  citationDocId: string
  citationVersion: number
  citationLabel: string
  status: 'pending' | 'published'
  sourceRef?: string
  tags: string[]
}

export interface KbSearchResult {
  id: string
  title: string
  excerpt: string
  spaceName: string
  docId: string
  version: number
  paragraph: string
}

export interface KbExpiryItem {
  id: string
  docId: string
  title: string
  kind: KbDocKind
  expiresOn: string
  daysRemaining: number
  owner: string
  status: 'upcoming' | 'expired'
}

export interface KbAccessLog {
  id: string
  docId: string
  title: string
  actor: string
  actorRole: Role
  action: 'view' | 'download' | 'ai_read'
  at: string
  origin: 'human' | 'ai'
  agentSuggestionId?: string
}

export interface EmployeeFile {
  id: string
  employeeId: string
  name: string
  kind: 'contract' | 'id_copy' | 'certificate'
  expiresOn: string | null
  sensitive: boolean
  uploadedAt: string
  size: string
}

export interface OnboardingChecklistItem {
  id: string
  roleId: string
  title: string
  description: string
  route: string
  done: boolean
}

export interface OnboardingAnswer {
  answer: string
  citations: Array<{ label: string; href: string; docId: string; version: number }>
}
