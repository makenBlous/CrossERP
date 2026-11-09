import type { MockDatabase } from '@/types/entities'

export function nextId(db: MockDatabase, prefix: string): string {
  db.meta.seq += 1

  return `${prefix}-${String(db.meta.seq).padStart(5, '0')}`
}

export function mustFind<T extends { id: string }>(rows: T[], id: string, label: string): T {
  const found = rows.find(row => row.id === id)

  if (!found)
    throw new Error(`找不到${label}: ${id}`)

  return found
}
