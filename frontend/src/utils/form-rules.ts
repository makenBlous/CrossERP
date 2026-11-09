export function requiredText(message: string) {
  return (value: unknown) => {
    if (value === null || value === undefined || String(value).trim() === '')
      return message

    return true
  }
}

export function numberText(message: string) {
  return (value: unknown) => {
    if (value === '' || value === null || value === undefined)
      return true

    return /^-?\d+(?:\.\d+)?$/.test(String(value).trim()) || message
  }
}

export function moneyText(message: string) {
  return (value: unknown) => {
    if (value === '' || value === null || value === undefined)
      return true

    return /^-?\d+(?:\.\d{1,4})?$/.test(String(value).trim()) || message
  }
}
