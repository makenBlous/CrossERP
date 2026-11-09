import { assertPermission, database, delay } from '@/api/mock-client'
import type { BundleDraft, CostDraft, ListingDraft, MappingDraft, NamedDraft, SkuDraft } from '@/mocks/services/catalog'
import {
  projectBrands,
  projectBundles,
  projectCategories,
  projectCosts,
  projectListing,
  projectListings,
  projectLookups,
  projectMappings,
  projectSkuDetail,
  projectSkuRows,
} from '@/mocks/project-ops'

// 未来: GET /api/v1/catalog/skus
export async function fetchSkus() {
  await delay()
  assertPermission('item:read')

  return projectSkuRows(database().db)
}

// 未来: GET /api/v1/catalog/skus/{id}
export async function fetchSku(id: string) {
  await delay()
  assertPermission('item:read')

  return projectSkuDetail(database().db, id)
}

// 未来: POST /api/v1/catalog/skus
export async function createSku(input: SkuDraft) {
  await delay()

  return database().saveSku(input, assertPermission('item:create'))
}

// 未来: PATCH /api/v1/catalog/skus/{id}
export async function updateSku(id: string, input: SkuDraft) {
  await delay()

  return database().saveSku({ ...input, id }, assertPermission('item:write'))
}

// 未来: POST /api/v1/catalog/skus/status
export async function changeSkuActive(ids: string[], active: boolean) {
  await delay()
  database().setSkuActive(ids, active, assertPermission('item:write'))
}

// 未来: GET /api/v1/catalog/costs
export async function fetchCosts() {
  await delay()
  assertPermission('item:read')

  return projectCosts(database().db)
}

// 未来: POST /api/v1/catalog/costs
export async function createCost(input: CostDraft) {
  await delay()

  return database().addSkuCost(input, assertPermission('item:write'))
}

// 未来: GET /api/v1/catalog/listings
export async function fetchListings() {
  await delay()
  assertPermission('listing:read')

  return projectListings(database().db)
}

// 未来: GET /api/v1/catalog/listings/{id}
export async function fetchListing(id: string) {
  await delay()
  assertPermission('listing:read')

  return projectListing(database().db, id)
}

// 未来: POST /api/v1/catalog/listings
export async function createListing(input: ListingDraft) {
  await delay()

  return database().saveListing(input, assertPermission('listing:create'))
}

// 未来: PATCH /api/v1/catalog/listings/{id}
export async function updateListing(id: string, input: ListingDraft) {
  await delay()

  return database().saveListing({ ...input, id }, assertPermission('listing:write'))
}

// 未来: POST /api/v1/catalog/listings/status
export async function changeListingStatus(ids: string[], status: string) {
  await delay()
  database().setListingStatus(ids, status, assertPermission('listing:write'))
}

// 未来: GET /api/v1/catalog/categories
export async function fetchCategories() {
  await delay()
  assertPermission('item_group:read')

  return projectCategories(database().db)
}

// 未来: POST /api/v1/catalog/categories
export async function createCategory(input: NamedDraft) {
  await delay()

  return database().saveCategory(input, assertPermission('item_group:create'))
}

// 未来: PATCH /api/v1/catalog/categories/{id}
export async function updateCategory(id: string, input: NamedDraft) {
  await delay()

  return database().saveCategory({ ...input, id }, assertPermission('item_group:write'))
}

// 未来: POST /api/v1/catalog/categories/status
export async function changeCategoryActive(ids: string[], active: boolean) {
  await delay()
  database().setCategoryActive(ids, active, assertPermission('item_group:write'))
}

// 未来: GET /api/v1/catalog/brands
export async function fetchBrands() {
  await delay()
  assertPermission('brand:read')

  return projectBrands(database().db)
}

// 未来: POST /api/v1/catalog/brands
export async function createBrand(input: NamedDraft) {
  await delay()

  return database().saveBrand(input, assertPermission('brand:create'))
}

// 未来: PATCH /api/v1/catalog/brands/{id}
export async function updateBrand(id: string, input: NamedDraft) {
  await delay()

  return database().saveBrand({ ...input, id }, assertPermission('brand:write'))
}

// 未来: POST /api/v1/catalog/brands/status
export async function changeBrandActive(ids: string[], active: boolean) {
  await delay()
  database().setBrandActive(ids, active, assertPermission('brand:write'))
}

// 未来: GET /api/v1/catalog/mappings
export async function fetchMappings() {
  await delay()
  assertPermission('listing:read')

  return projectMappings(database().db)
}

// 未来: POST /api/v1/catalog/mappings
export async function createMapping(input: MappingDraft) {
  await delay()

  return database().saveMapping(input, assertPermission('item:write'))
}

// 未来: POST /api/v1/catalog/mappings/confirm
export async function confirmMappingRows(ids: string[]) {
  await delay()
  database().confirmMappings(ids, assertPermission('item:write'))
}

// 未来: GET /api/v1/catalog/bundles
export async function fetchBundles() {
  await delay()
  assertPermission('item:read')

  return projectBundles(database().db)
}

// 未来: POST /api/v1/catalog/bundles
export async function createBundle(input: BundleDraft) {
  await delay()

  return database().saveBundle(input, assertPermission('item:write'))
}

// 未来: PATCH /api/v1/catalog/bundles/{id}
export async function updateBundle(id: string, input: BundleDraft) {
  await delay()

  return database().saveBundle({ ...input, id }, assertPermission('item:write'))
}

// 未来: DELETE /api/v1/catalog/bundles
export async function deleteBundles(ids: string[]) {
  await delay()
  database().removeBundles(ids, assertPermission('item:delete'))
}

// 未来: GET /api/v1/catalog/lookups
export async function fetchCatalogLookups() {
  await delay()
  assertPermission('item:read')

  return projectLookups(database().db)
}
