export function useChatHistory<T extends { id: string }>(scope: string) {
  const key = `crosserp-chat-history:${scope}`

  function read(): T[] {
    if (typeof localStorage === 'undefined')
      return []

    try {
      const value = JSON.parse(localStorage.getItem(key) ?? '[]') as unknown

      return Array.isArray(value) ? value as T[] : []
    }
    catch {
      return []
    }
  }

  function load(seed: T[]) {
    const merged = new Map<string, T>()

    for (const item of seed)
      merged.set(item.id, item)
    for (const item of read())
      merged.set(item.id, item)

    return [...merged.values()]
  }

  function save(items: T[]) {
    if (typeof localStorage === 'undefined')
      return

    localStorage.setItem(key, JSON.stringify(items))
  }

  function clear() {
    if (typeof localStorage !== 'undefined')
      localStorage.removeItem(key)
  }

  return { load, save, clear }
}
