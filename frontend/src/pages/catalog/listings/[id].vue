<script setup lang="ts">
import { fetchListing, updateListing } from '@/api/catalog'
import DetailPage from '@/components/biz/DetailPage.vue'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import { usePageContext } from '@/composables/usePageContext'
import type { CurrencyCode, ListingListRow } from '@/types/domain'
import { moneyText, requiredText } from '@/utils/form-rules'
import { readParam } from '@/utils/route-param'

const route = useRoute()
const { t } = useI18n({ useScope: 'global' })
const { setSelected } = usePageContext()
const listing = ref<ListingListRow | null>(null)
const loaded = ref(false)
const error = ref('')
const open = ref(false)
const saving = ref(false)
const currencies: CurrencyCode[] = ['USD', 'EUR', 'GBP', 'JPY', 'CNY']
const form = reactive({ title: '', status: 'active', price: '', currency: 'USD' as CurrencyCode, platformListingId: '' })

const listingId = computed(() => readParam(route.params, 'id'))

async function load() {
  loaded.value = false
  error.value = ''
  try {
    listing.value = await fetchListing(listingId.value)
    if (listing.value) {
      form.title = listing.value.title
      form.status = listing.value.status
      form.price = String(listing.value.price)
      form.currency = listing.value.currency
      form.platformListingId = listing.value.platformListingId
    }
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loaded.value = true
  }
}

onMounted(load)
watch(listingId, load)
watch(listing, value => setSelected(value?.id ?? null))
onUnmounted(() => setSelected(null))

const related = computed(() => {
  if (!listing.value)
    return []

  return [{
    id: listing.value.skuId,
    type: 'SKU',
    label: listing.value.internalSku,
    to: `/catalog/skus/${listing.value.skuId}`,
  }]
})

async function save() {
  if (!listing.value)
    return

  saving.value = true
  error.value = ''
  try {
    await updateListing(listing.value.id, {
      storeId: listing.value.storeId,
      skuId: listing.value.skuId,
      platformListingId: form.platformListingId,
      title: form.title,
      status: form.status,
      price: form.price,
      currency: form.currency,
    })
    open.value = false
    await load()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <VBtn
      variant="text"
      class="mb-4"
      prepend-icon="tabler-arrow-left"
      :to="{ path: '/catalog/listings' }"
    >
      {{ t('catalog.listingTitle') }}
    </VBtn>
    <VAlert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-4"
    >
      {{ error }}
    </VAlert>
    <LoadingState v-if="!loaded" />
    <VAlert
      v-else-if="!listing"
      type="warning"
      variant="tonal"
    >
      {{ t('catalog.missingListing') }}
    </VAlert>
    <DetailPage
      v-else
      :title="listing.title"
      :subtitle="`${listing.platform} · ${listing.marketplace} · ${listing.storeName}`"
      domain="generic"
      :status="listing.status"
      :related="related"
    >
      <template #actions>
        <PermissionGate action="update">
          <VBtn
            color="primary"
            @click="open = true"
          >
            {{ t('catalog.editListing') }}
          </VBtn>
        </PermissionGate>
      </template>
      <VCard>
        <VRow>
          <VCol
            cols="12"
            md="4"
          >
            <VImg
              src="/images/svg/gift.svg"
              height="180"
              contain
            />
          </VCol>
          <VCol
            cols="12"
            md="8"
          >
            <VCardText>
              <div class="mb-2">
                {{ t('catalog.listingId') }}：{{ listing.platformListingId }}
              </div>
              <div class="mb-2">
                {{ t('catalog.mappedSku') }}：
                <RouterLink :to="{ path: `/catalog/skus/${listing.skuId}` }">
                  {{ listing.internalSku }}
                </RouterLink>
              </div>
              <div>
                {{ t('catalog.price') }}：
                <MoneyText
                  :amount="listing.price"
                  :currency="listing.currency"
                />
              </div>
            </VCardText>
          </VCol>
        </VRow>
      </VCard>
    </DetailPage>
    <FormDrawer
      v-model="open"
      :title="t('catalog.editListing')"
      :saving="saving"
      @save="save"
    >
      <AppTextField
        v-model="form.title"
        :label="t('catalog.name')"
        :rules="[requiredText(t('catalog.name'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.platformListingId"
        :label="t('catalog.listingId')"
        :rules="[requiredText(t('catalog.listingId'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="form.status"
        :items="['active', 'paused', 'disabled']"
        :label="t('common.status')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.price"
        :label="t('catalog.price')"
        :rules="[requiredText(t('catalog.price')), moneyText(t('catalog.price'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="form.currency"
        :items="currencies"
        :label="t('common.amount')"
      />
    </FormDrawer>
  </div>
</template>
