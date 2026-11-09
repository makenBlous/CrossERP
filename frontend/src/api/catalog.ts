import { assertCan, database, delay } from '@/api/mock-client'
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

  return projectSkuRows(database().db)
}

// 未来: GET /api/v1/catalog/skus/{id}
export async function fetchSku(id: string) {
  await delay()

  return projectSkuDetail(database().db, id)
}

// 未来: POST /api/v1/catalog/skus
export async function createSku(input: SkuDraft) {
  await delay()

  return database().saveSku(input, assertCan('create'))
}

// 未来: PATCH /api/v1/catalog/skus/{id}
export async function updateSku(id: string, input: SkuDraft) {
  await delay()

  return database().saveSku({ ...input, id }, assertCan('update'))
}

// 未来: POST /api/v1/catalog/skus/status
export async function changeSkuActive(ids: string[], active: boolean) {
  await delay()
  database().setSkuActive(ids, active, assertCan('update'))
}

// 未来: GET /api/v1/catalog/costs
export async function fetchCosts() {
  await delay()

  return projectCosts(database().db)
}

// 未来: POST /api/v1/catalog/costs
export async function createCost(input: CostDraft) {
  await delay()

  return database().addSkuCost(input, assertCan('create'))
}

// 未来: GET /api/v1/catalog/listings
export async function fetchListings() {
  await delay()

  return projectListings(database().db)
}

// 未来: GET /api/v1/catalog/listings/{id}
export async function fetchListing(id: string) {
  await delay()

  return projectListing(database().db, id)
}

// 未来: POST /api/v1/catalog/listings
export async function createListing(input: ListingDraft) {
  await delay()

  return database().saveListing(input, assertCan('create'))
}

// 未来: PATCH /api/v1/catalog/listings/{id}
export async function updateListing(id: string, input: ListingDraft) {
  await delay()

  return database().saveListing({ ...input, id }, assertCan('update'))
}

// 未来: POST /api/v1/catalog/listings/status
export async function changeListingStatus(ids: string[], status: string) {
  await delay()
  database().setListingStatus(ids, status, assertCan('update'))
}

// 未来: GET /api/v1/catalog/categories
export async function fetchCategories() {
  await delay()

  return projectCategories(database().db)
}

// 未来: POST /api/v1/catalog/categories
export async function createCategory(input: NamedDraft) {
  await delay()

  return database().saveCategory(input, assertCan('create'))
}

// 未来: PATCH /api/v1/catalog/categories/{id}
export async function updateCategory(id: string, input: NamedDraft) {
  await delay()

  return database().saveCategory({ ...input, id }, assertCan('update'))
}

// 未来: POST /api/v1/catalog/categories/status
export async function changeCategoryActive(ids: string[], active: boolean) {
  await delay()
  database().setCategoryActive(ids, active, assertCan('update'))
}

// 未来: GET /api/v1/catalog/brands
export async function fetchBrands() {
  await delay()

  return projectBrands(database().db)
}

// 未来: POST /api/v1/catalog/brands
export async function createBrand(input: NamedDraft) {
  await delay()

  return database().saveBrand(input, assertCan('create'))
}

// 未来: PATCH /api/v1/catalog/brands/{id}
export async function updateBrand(id: string, input: NamedDraft) {
  await delay()

  return database().saveBrand({ ...input, id }, assertCan('update'))
}

// 未来: POST /api/v1/catalog/brands/status
export async function changeBrandActive(ids: string[], active: boolean) {
  await delay()
  database().setBrandActive(ids, active, assertCan('update'))
}

// 未来: GET /api/v1/catalog/mappings
export async function fetchMappings() {
  await delay()

  return projectMappings(database().db)
}

// 未来: POST /api/v1/catalog/mappings
export async function createMapping(input: MappingDraft) {
  await delay()

  return database().saveMapping(input, assertCan('create'))
}

// 未来: POST /api/v1/catalog/mappings/confirm
export async function confirmMappingRows(ids: string[]) {
  await delay()
  database().confirmMappings(ids, assertCan('update'))
}

// 未来: GET /api/v1/catalog/bundles
export async function fetchBundles() {
  await delay()

  return projectBundles(database().db)
}

// 未来: POST /api/v1/catalog/bundles
export async function createBundle(input: BundleDraft) {
  await delay()

  return database().saveBundle(input, assertCan('create'))
}

// 未来: PATCH /api/v1/catalog/bundles/{id}
export async function updateBundle(id: string, input: BundleDraft) {
  await delay()

  return database().saveBundle({ ...input, id }, assertCan('update'))
}

// 未来: DELETE /api/v1/catalog/bundles
export async function deleteBundles(ids: string[]) {
  await delay()
  database().removeBundles(ids, assertCan('delete'))
}

// 未来: GET /api/v1/catalog/lookups
export async function fetchCatalogLookups() {
  await delay()

  return projectLookups(database().db)
}
