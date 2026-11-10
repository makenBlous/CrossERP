export type GapBKey =
  | 'S09' | 'S10' | 'S11' | 'S12' | 'S13'
  | 'I12' | 'I13' | 'I14' | 'I15' | 'D05'
  | 'INT01' | 'INT02' | 'INT03' | 'INT04' | 'INT05'
  | 'W08' | 'SYS19' | 'SYS20' | 'SYS25' | 'SYS26'

export type GapBKind = 'list' | 'detail' | 'form' | 'wizard'

export interface GapBColumn {
  key: string
  title: string
}

export interface GapBRow {
  id: string
  [key: string]: unknown
}

export interface GapBDetail {
  id: string
  title: string
  status?: string
  summary: string
  fields: Array<{ label: string; value: string }>
  steps: Array<{ id: string; title: string; detail: string; status: 'done' | 'open' | 'blocked' }>
  related: Array<{ id: string; type: string; label: string; to?: string }>
}

export interface GapBPageData {
  key: GapBKey
  title: string
  subtitle: string
  kind: GapBKind
  columns: GapBColumn[]
  rows: GapBRow[]
  detail?: GapBDetail
  message?: string
  audit: GapBAuditEvent[]
  chain?: GapBChainNode[]
}

export interface GapBAuditEvent {
  id: string
  at: string
  actorId: string
  actor: string
  action: string
  refType: string
  refId: string
  summary: string
  channel?: string
}

export interface GapBChainNode {
  id: string
  title: string
  detail: string
  status: 'connected' | 'pending'
  to?: string
}
