export function readParam(params: unknown, key: string) {
  if (!params || typeof params !== 'object')
    return ''

  const value = (params as Record<string, unknown>)[key]

  if (Array.isArray(value))
    return typeof value[0] === 'string' ? value[0] : ''

  return typeof value === 'string' ? value : ''
}
