import { type MaybeRefOrGetter, computed, toValue } from 'vue'

export interface LocalChatItem {
  id: string
  local?: boolean
}

export function useChatHistory<T extends LocalChatItem>(
  scope: MaybeRefOrGetter<string>,
  userId: MaybeRefOrGetter<string | null | undefined>,
  isLoggedIn: MaybeRefOrGetter<boolean>,
) {
  const cacheKey = computed(() => {
    const actor = toValue(userId)
    const scopeValue = toValue(scope)

    return toValue(isLoggedIn) && actor && scopeValue ? `crosserp-chat-history:${actor}:${scopeValue}` : null
  })

  function read(): T[] {
    const actor = toValue(userId)
    const key = cacheKey.value

    if (!toValue(isLoggedIn))
      return []

    if (!actor || !key || typeof localStorage === 'undefined')
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
    const seedIds = new Set(seed.map(item => item.id))
    const localItems = read().filter(item => item.local === true && !seedIds.has(item.id))

    return [...seed, ...localItems]
  }

  function save(items: T[]) {
    const actor = toValue(userId)
    const key = cacheKey.value

    if (!toValue(isLoggedIn))
      return

    if (!actor || !key || typeof localStorage === 'undefined')
      return

    localStorage.setItem(key, JSON.stringify(items.filter(item => item.local === true)))
  }

  function clear() {
    const actor = toValue(userId)
    const key = cacheKey.value

    if (toValue(isLoggedIn) && actor && key && typeof localStorage !== 'undefined')
      localStorage.removeItem(key)
  }

  return { cacheKey, load, save, clear }
}
