import type { AuditChainEntry } from '@/types/agent-module'
import type { AuditEvent, MockDatabase } from '@/types/entities'

function stable(value: string) {
  let hash = 2166136261
  for (const char of value) {
    hash ^= char.charCodeAt(0)
    hash = Math.imul(hash, 16777619)
  }

  return (hash >>> 0).toString(16).padStart(8, '0')
}

export function hashEvent(event: AuditEvent, prevHash: string) {
  return `demo-${stable(`${prevHash}|${event.id}|${event.at}|${event.actor}|${event.action}|${event.refType}|${event.refId}|${event.summary}`)}`
}

export function buildChain(db: MockDatabase, tamperedIndex = -1): AuditChainEntry[] {
  let previous = 'GENESIS'

  return db.audit.map((event, index) => {
    const prevHash = previous
    const hash = hashEvent(event, prevHash)
    const entry = { index, eventId: event.id, prevHash, hash: index === tamperedIndex ? `${hash}-tampered` : hash }

    previous = entry.hash

    return entry
  })
}

export function verifyChain(db: MockDatabase, tamperedIndex = -1) {
  const chain = buildChain(db, tamperedIndex)
  let previous = 'GENESIS'

  const brokenIndex = chain.findIndex((entry, index) => {
    const event = db.audit[index]
    const expected = event ? hashEvent(event, previous) : ''
    const broken = entry.prevHash !== previous || entry.hash !== expected

    previous = entry.hash

    return broken
  })

  return { ok: brokenIndex < 0, brokenIndex, chain }
}
