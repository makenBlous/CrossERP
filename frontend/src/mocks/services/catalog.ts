import type { Actor, Brand, Bundle, Category, Listing, MockDatabase, Sku, SkuCost, SkuMapping } from '@/types/entities'
import type { CurrencyCode } from '@/types/domain'
import { writeAudit } from '@/mocks/services/audit'
import { FlowError } from '@/mocks/services/errors'
import { mustFind, nextId } from '@/mocks/services/ids'
import { minorFromDecimal } from '@/utils/money'

export interface SkuDraft {
  internalSku: string
  title: string
  titleEn: string
  brandId: string
  categoryId: string
}

export interface CostDraft {
  internalSku: string
  validFrom: string
  unitCost: string
  freightPerUnit: string
  currency: CurrencyCode
}

export interface ListingDraft {
  id?: string
  storeId: string
  skuId: string
  platformListingId: string
  title: string
  status: string
  price: string
  currency: CurrencyCode
}

export interface NamedDraft {
  id?: string
  name: string
  parentId?: string | null
  sortNo?: number
}

export interface MappingDraft {
  id?: string
  storeId: string
  platformSku: string
  internalSku: string
  status: 'confirmed' | 'suggested'
}

export interface BundleDraft {
  id?: string
  parentInternalSku: string
  childInternalSku: string
  qty: number
}

function dayBefore(isoDate: string) {
  const [year, month, day] = isoDate.slice(0, 10).split('-').map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))

  date.setUTCDate(date.getUTCDate() - 1)

  return date.toISOString().slice(0, 10)
}

export function saveSku(db: MockDatabase, input: SkuDraft & { id?: string }, actor: Actor): Sku {
  const code = input.internalSku.trim()

  if (!code || !input.title.trim())
    throw new FlowError('请填写内部货号和名称')

  const duplicated = db.skus.find(item => item.internalSku === code && item.id !== input.id)

  if (duplicated)
    throw new FlowError(`货号 ${code} 已存在`)

  mustFind(db.brands, input.brandId, '品牌')
  mustFind(db.categories, input.categoryId, '类目')

  if (input.id) {
    const sku = mustFind(db.skus, input.id, 'SKU')

    sku.internalSku = code
    sku.title = input.title.trim()
    if (input.titleEn.trim())
      sku.titleEn = input.titleEn.trim()

    sku.brandId = input.brandId
    sku.categoryId = input.categoryId
    writeAudit(db, actor, 'update', 'sku', sku.id, `更新 SKU ${sku.internalSku}`)

    return sku
  }

  const sku: Sku = {
    id: nextId(db, 'sku'),
    internalSku: code,
    title: input.title.trim(),
    titleEn: input.titleEn.trim() || input.title.trim(),
    brandId: input.brandId,
    categoryId: input.categoryId,
    active: true,
  }

  db.skus.push(sku)
  writeAudit(db, actor, 'create', 'sku', sku.id, `新建 SKU ${sku.internalSku}`)

  return sku
}

export function setSkuActive(db: MockDatabase, ids: string[], active: boolean, actor: Actor) {
  for (const id of ids) {
    const sku = mustFind(db.skus, id, 'SKU')

    sku.active = active
    writeAudit(db, actor, active ? 'enable' : 'disable', 'sku', sku.id, `${active ? '启用' : '停用'} SKU ${sku.internalSku}`)
  }
}

export function addSkuCost(db: MockDatabase, input: CostDraft, actor: Actor): SkuCost {
  const sku = db.skus.find(item => item.internalSku === input.internalSku.trim())

  if (!sku)
    throw new FlowError(`找不到货号 ${input.internalSku}`)

  const currencies = ['USD', 'CNY', 'EUR', 'GBP', 'JPY']

  if (!currencies.includes(input.currency))
    throw new FlowError('币种只能是 USD、CNY、EUR、GBP、JPY')

  const validFrom = input.validFrom.slice(0, 10)

  if (!/^\d{4}-\d{2}-\d{2}$/.test(validFrom))
    throw new FlowError('生效日格式应为 YYYY-MM-DD')

  const unitCost = minorFromDecimal(input.unitCost)
  const freight = minorFromDecimal(input.freightPerUnit)
  const open = db.skuCosts.filter(item => item.internalSku === sku.internalSku && item.validTo === null)

  for (const row of open) {
    if (validFrom <= row.validFrom)
      throw new FlowError(`新生效日必须晚于当前期间 ${row.validFrom}`)

    row.validTo = dayBefore(validFrom)
  }

  const cost: SkuCost = {
    id: nextId(db, 'cost'),
    internalSku: sku.internalSku,
    validFrom,
    validTo: null,
    unitCost,
    currency: input.currency,
    freightPerUnit: freight,
  }

  db.skuCosts.push(cost)
  writeAudit(db, actor, 'create', 'sku_cost', cost.id, `新增 ${sku.internalSku} 成本生效期 ${validFrom}`)

  return cost
}

export function saveListing(db: MockDatabase, input: ListingDraft, actor: Actor): Listing {
  const store = mustFind(db.stores, input.storeId, '店铺')
  const sku = mustFind(db.skus, input.skuId, 'SKU')
  const price = minorFromDecimal(input.price)

  if (input.id) {
    const listing = mustFind(db.listings, input.id, 'Listing')

    listing.title = input.title.trim()
    listing.status = input.status
    listing.price = price
    listing.currency = input.currency
    listing.platformListingId = input.platformListingId.trim()
    writeAudit(db, actor, 'update', 'listing', listing.id, `更新 Listing ${listing.platformListingId}`)

    return listing
  }

  const listing: Listing = {
    id: nextId(db, 'lst'),
    storeId: store.id,
    skuId: sku.id,
    platformListingId: input.platformListingId.trim(),
    title: input.title.trim() || sku.title,
    status: input.status || 'active',
    price,
    currency: input.currency,
  }

  db.listings.push(listing)
  writeAudit(db, actor, 'create', 'listing', listing.id, `新建 Listing ${listing.platformListingId}`)

  return listing
}

export function setListingStatus(db: MockDatabase, ids: string[], status: string, actor: Actor) {
  for (const id of ids) {
    const listing = mustFind(db.listings, id, 'Listing')

    listing.status = status
    writeAudit(db, actor, 'update', 'listing', listing.id, `Listing ${listing.platformListingId} 状态改为 ${status}`)
  }
}

export function saveCategory(db: MockDatabase, input: NamedDraft, actor: Actor): Category {
  const name = input.name.trim()

  if (!name)
    throw new FlowError('请填写类目名称')

  if (db.categories.some(item => item.name === name && item.id !== input.id))
    throw new FlowError(`类目 ${name} 已存在`)

  if (input.parentId)
    mustFind(db.categories, input.parentId, '上级类目')

  if (input.id) {
    const row = mustFind(db.categories, input.id, '类目')

    if (input.parentId === row.id)
      throw new FlowError('类目不能把自己设为上级')

    row.name = name
    row.parentId = input.parentId || null
    row.sortNo = input.sortNo ?? row.sortNo
    writeAudit(db, actor, 'update', 'category', row.id, `更新类目 ${row.name}`)

    return row
  }

  const row: Category = {
    id: nextId(db, 'cat'),
    parentId: input.parentId || null,
    name,
    sortNo: input.sortNo ?? db.categories.length + 1,
    active: true,
  }

  db.categories.push(row)
  writeAudit(db, actor, 'create', 'category', row.id, `新建类目 ${row.name}`)

  return row
}

export function setCategoryActive(db: MockDatabase, ids: string[], active: boolean, actor: Actor) {
  for (const id of ids) {
    const row = mustFind(db.categories, id, '类目')

    row.active = active
    writeAudit(db, actor, active ? 'enable' : 'disable', 'category', row.id, `${active ? '启用' : '停用'}类目 ${row.name}`)
  }
}

export function saveBrand(db: MockDatabase, input: NamedDraft, actor: Actor): Brand {
  const name = input.name.trim()

  if (!name)
    throw new FlowError('请填写品牌名称')

  if (db.brands.some(item => item.name === name && item.id !== input.id))
    throw new FlowError(`品牌 ${name} 已存在`)

  if (input.id) {
    const row = mustFind(db.brands, input.id, '品牌')

    row.name = name
    writeAudit(db, actor, 'update', 'brand', row.id, `更新品牌 ${row.name}`)

    return row
  }

  const row: Brand = { id: nextId(db, 'br'), name, active: true }

  db.brands.push(row)
  writeAudit(db, actor, 'create', 'brand', row.id, `新建品牌 ${row.name}`)

  return row
}

export function setBrandActive(db: MockDatabase, ids: string[], active: boolean, actor: Actor) {
  for (const id of ids) {
    const row = mustFind(db.brands, id, '品牌')

    row.active = active
    writeAudit(db, actor, active ? 'enable' : 'disable', 'brand', row.id, `${active ? '启用' : '停用'}品牌 ${row.name}`)
  }
}

export function saveMapping(db: MockDatabase, input: MappingDraft, actor: Actor): SkuMapping {
  const store = mustFind(db.stores, input.storeId, '店铺')
  const sku = db.skus.find(item => item.internalSku === input.internalSku.trim())

  if (!sku)
    throw new FlowError(`找不到内部货号 ${input.internalSku}`)

  const platformSku = input.platformSku.trim()

  if (!platformSku)
    throw new FlowError('请填写平台货号')

  const duplicated = db.mappings.find(item => item.storeId === store.id && item.platformSku === platformSku && item.id !== input.id)

  if (duplicated)
    throw new FlowError(`店铺内平台货号 ${platformSku} 已有映射`)

  if (input.id) {
    const row = mustFind(db.mappings, input.id, '映射')

    row.storeId = store.id
    row.platformSku = platformSku
    row.internalSku = sku.internalSku
    row.status = input.status
    writeAudit(db, actor, 'update', 'sku_mapping', row.id, `更新映射 ${row.platformSku} → ${row.internalSku}`)

    return row
  }

  const row: SkuMapping = {
    id: nextId(db, 'map'),
    storeId: store.id,
    platformSku,
    internalSku: sku.internalSku,
    status: input.status,
  }

  db.mappings.push(row)
  writeAudit(db, actor, 'create', 'sku_mapping', row.id, `新建映射 ${row.platformSku} → ${row.internalSku}（${row.status}）`)

  return row
}

export function confirmMappings(db: MockDatabase, ids: string[], actor: Actor) {
  for (const id of ids) {
    const row = mustFind(db.mappings, id, '映射')

    row.status = 'confirmed'
    writeAudit(db, actor, 'confirm', 'sku_mapping', row.id, `人工确认映射 ${row.platformSku} → ${row.internalSku}`)
  }
}

export function saveBundle(db: MockDatabase, input: BundleDraft, actor: Actor): Bundle {
  const parent = db.skus.find(item => item.internalSku === input.parentInternalSku.trim())
  const child = db.skus.find(item => item.internalSku === input.childInternalSku.trim())

  if (!parent || !child)
    throw new FlowError('主件和子件都必须是已有货号')

  if (parent.internalSku === child.internalSku)
    throw new FlowError('主件和子件不能相同')

  if (!Number.isInteger(input.qty) || input.qty < 1)
    throw new FlowError('子件数量必须是正整数')

  if (input.id) {
    const row = mustFind(db.bundles, input.id, '组合装')

    row.parentInternalSku = parent.internalSku
    row.childInternalSku = child.internalSku
    row.qty = input.qty
    writeAudit(db, actor, 'update', 'bundle', row.id, `更新组合装 ${row.parentInternalSku}`)

    return row
  }

  const row: Bundle = {
    id: nextId(db, 'bun'),
    parentInternalSku: parent.internalSku,
    childInternalSku: child.internalSku,
    qty: input.qty,
  }

  db.bundles.push(row)
  writeAudit(db, actor, 'create', 'bundle', row.id, `新建组合装 ${row.parentInternalSku} × ${row.childInternalSku}`)

  return row
}

export function removeBundles(db: MockDatabase, ids: string[], actor: Actor) {
  for (const id of ids) {
    const row = mustFind(db.bundles, id, '组合装')

    db.bundles = db.bundles.filter(item => item.id !== id)
    writeAudit(db, actor, 'delete', 'bundle', id, `删除组合装 ${row.parentInternalSku} × ${row.childInternalSku}`)
  }
}
