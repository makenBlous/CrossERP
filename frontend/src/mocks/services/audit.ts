import type { Actor, MockDatabase } from '@/types/entities'
import { nextId } from '@/mocks/services/ids'

export function writeAudit(
  db: MockDatabase,
  actor: Actor,
  action: string,
  refType: string,
  refId: string,
  summary: string,
  metadata: { confirmerId?: string } = {},
) {
  db.audit.push({
    id: nextId(db, 'aud'),
    at: actor.at,
    actorId: actor.userId,
    actor: actor.name,
    actorRole: actor.role,
    ...metadata,
    action,
    refType,
    refId,
    summary,
  })
}
