import type { Actor, MockDatabase } from '@/types/entities'
import { nextId } from '@/mocks/services/ids'

export function writeAudit(
  db: MockDatabase,
  actor: Actor,
  action: string,
  refType: string,
  refId: string,
  summary: string,
) {
  db.audit.push({
    id: nextId(db, 'aud'),
    at: actor.at,
    actorId: actor.id ?? `role:${actor.role}`,
    actor: actor.name,
    actorRole: actor.role,
    action,
    refType,
    refId,
    summary,
  })
}
