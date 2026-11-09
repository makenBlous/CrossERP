import { isEmpty, isEmptyArray, isNullOrUndefined } from './helpers'

type ValidatorTranslator = (key: string, params?: Record<string, unknown>) => string
let translate: ValidatorTranslator = (key, params = {}) => ({
  'validation.required': '此字段为必填项',
  'validation.email': '请输入有效的邮箱地址',
  'validation.password': '密码至少 8 位，并包含大小写字母、数字和特殊字符',
  'validation.confirmed': '两次输入的内容不一致',
  'validation.between': '请输入范围内的数字',
  'validation.integer': '请输入整数',
  'validation.regex': '字段格式不正确',
  'validation.alpha': '只能包含英文字母',
  'validation.url': '请输入有效的网址',
  'validation.length': '字段长度不符合要求',
  'validation.alphaDash': '只能包含字母、数字、下划线或连字符',
  'validation.number': '请输入数字',
  'validation.money': '请输入最多 4 位小数的金额',
}[key] ?? key).replace(/\$\{(\w+)\}/g, (_, name) => String(params[name] ?? ''))

export function configureValidatorI18n(fn: ValidatorTranslator) {
  translate = fn
}

// 👉 Required Validator
export const requiredValidator = (value: unknown) => {
  if (isNullOrUndefined(value) || isEmptyArray(value) || value === false)
    return translate('validation.required')

  return !!String(value).trim().length || translate('validation.required')
}

// 👉 Email Validator
export const emailValidator = (value: unknown) => {
  if (isEmpty(value))
    return true

  const re = /^(?:[^<>()[\]\\.,;:\s@"]+(?:\.[^<>()[\]\\.,;:\s@"]+)*|".+")@(?:\[\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\]|(?:[a-z\-\d]+\.)+[a-z]{2,})$/i

  if (Array.isArray(value))
    return value.every(val => re.test(String(val))) || translate('validation.email')

  return re.test(String(value)) || translate('validation.email')
}

// 👉 Password Validator
export const passwordValidator = (password: string) => {
  const regExp = /(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%&*()]).{8,}/

  const validPassword = regExp.test(password)

  return validPassword || translate('validation.password')
}

// 👉 Confirm Password Validator
export const confirmedValidator = (value: string, target: string) =>

  value === target || translate('validation.confirmed')

// 👉 Between Validator
export const betweenValidator = (value: unknown, min: number, max: number) => {
  const valueAsNumber = Number(value)

  return (Number(min) <= valueAsNumber && Number(max) >= valueAsNumber) || translate('validation.between', { min, max })
}

// 👉 Integer Validator
export const integerValidator = (value: unknown) => {
  if (isEmpty(value))
    return true

  if (Array.isArray(value))
    return value.every(val => /^-?\d+$/.test(String(val))) || translate('validation.integer')

  return /^-?\d+$/.test(String(value)) || translate('validation.integer')
}

// 👉 Regex Validator
export const regexValidator = (value: unknown, regex: RegExp | string): string | boolean => {
  if (isEmpty(value))
    return true

  let regeX = regex
  if (typeof regeX === 'string')
    regeX = new RegExp(regeX)

  if (Array.isArray(value))
    return value.every(val => regexValidator(val, regeX))

  return regeX.test(String(value)) || translate('validation.regex')
}

// 👉 Alpha Validator
export const alphaValidator = (value: unknown) => {
  if (isEmpty(value))
    return true

  return /^[A-Z]*$/i.test(String(value)) || translate('validation.alpha')
}

// 👉 URL Validator
export const urlValidator = (value: unknown) => {
  if (isEmpty(value))
    return true

  const re = /^https?:\/\/[^\s$.?#].\S*$/

  return re.test(String(value)) || translate('validation.url')
}

// 👉 Length Validator
export const lengthValidator = (value: unknown, length: number) => {
  if (isEmpty(value))
    return true

  return String(value).length === length || translate('validation.length', { length })
}

// 👉 Alpha-dash Validator
export const alphaDashValidator = (value: unknown) => {
  if (isEmpty(value))
    return true

  const valueAsString = String(value)

  return /^[\w-]*$/.test(valueAsString) || translate('validation.alphaDash')
}

// 👉 Decimal Validator
// full-version 只有 integerValidator，没有小数/金额校验。这里沿用它的写法。
export const decimalValidator = (value: unknown) => {
  if (isEmpty(value))
    return true

  return /^-?\d+(?:\.\d+)?$/.test(String(value).trim()) || translate('validation.number')
}

// 👉 Money Validator
// 金额最多 4 位小数，和 Money4 列一致。full-version 没有对应函数。
export const moneyValidator = (value: unknown) => {
  if (isEmpty(value))
    return true

  return /^-?\d+(?:\.\d{1,4})?$/.test(String(value).trim()) || translate('validation.money')
}

export function requiredText(message: string) {
  return (value: unknown) => requiredValidator(value) === true || message
}

export function numberText(message: string) {
  return (value: unknown) => {
    if (value === '' || value === null || value === undefined)
      return true

    return decimalValidator(value) === true || message
  }
}

export function moneyText(message: string) {
  return (value: unknown) => {
    if (value === '' || value === null || value === undefined)
      return true

    return moneyValidator(value) === true || message
  }
}
