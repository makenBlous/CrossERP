<script setup lang="ts">
import { changeSkuActive, createCost, fetchSku } from '@/api/catalog'
import DetailPage from '@/components/biz/DetailPage.vue'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { usePageContext } from '@/composables/usePageContext'
import type { CurrencyCode, SkuDetailView } from '@/types/domain'
import { moneyText, requiredText } from '@/utils/form-rules'
import { readParam } from '@/utils/route-param'

const route = useRoute()
const { t } = useI18n({ useScope: 'global' })
const { setSelected } = usePageContext()
const sku = ref<SkuDetailView | null>(null)
const loaded = ref(false)
const error = ref('')
const open = ref(false)
const saving = ref(false)
const currencies: CurrencyCode[] = ['CNY', 'USD', 'EUR', 'GBP', 'JPY']
const form = reactive({ validFrom: '2026-11-01', unitCost: '', freightPerUnit: '', currency: 'CNY' as CurrencyCode })

const skuId = computed(() => readParam(route.params, 'id'))

async function load() {
  loaded.value = false
  error.value = ''
  try {
    sku.value = await fetchSku(skuId.value)
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loaded.value = true
  }
}

onMounted(load)
watch(skuId, load)
watch(sku, value => setSelected(value?.id ?? null))
onUnmounted(() => setSelected(null))

const timeline = computed(() => (sku.value?.costs ?? []).map(item => ({
  id: item.id,
  at: item.validFrom,
  title: t('catalog.costTimeline'),
  detail: `${item.unitCost} ${item.currency} / ${t('catalog.freight')} ${item.freight}`,
})))

const related = computed(() => (sku.value?.orders ?? []).slice(0, 8).map(item => ({
  id: item.id,
  type: t('orders.title'),
  label: item.orderNo,
  to: `/orders/${item.id}`,
})))

async function toggle() {
  if (!sku.value)
    return

  error.value = ''
  try {
    await changeSkuActive([sku.value.id], sku.value.status !== 'active')
    await load()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}

async function saveCost() {
  if (!sku.value)
    return

  saving.value = true
  error.value = ''
  try {
    await createCost({
      internalSku: sku.value.internalSku,
      validFrom: form.validFrom,
      unitCost: form.unitCost,
      freightPerUnit: form.freightPerUnit,
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
      :to="{ path: '/catalog/skus' }"
    >
      {{ t('catalog.skuTitle') }}
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
      v-else-if="!sku"
      type="warning"
      variant="tonal"
    >
      {{ t('catalog.missingSku') }}
    </VAlert>
    <DetailPage
      v-else
      :title="sku.internalSku"
      :subtitle="`${sku.title} · ${sku.titleEn}`"
      domain="generic"
      :status="sku.status"
      :timeline="timeline"
      :related="related"
    >
      <template #actions>
        <PermissionGate action="create">
          <VBtn
            color="primary"
            @click="open = true"
          >
            {{ t('catalog.addCost') }}
          </VBtn>
        </PermissionGate>
        <PermissionGate action="update">
          <VBtn
            variant="tonal"
            @click="toggle"
          >
            {{ sku.status === 'active' ? t('catalog.disable') : t('catalog.enable') }}
          </VBtn>
        </PermissionGate>
      </template>
      <VCard class="mb-4">
        <VCardItem>
          <VCardTitle>{{ t('catalog.basics') }}</VCardTitle>
        </VCardItem>
        <VCardText>
          <div class="mb-2">
            {{ t('catalog.brand') }}：{{ sku.brandName }}
          </div>
          <div class="mb-2">
            {{ t('catalog.category') }}：{{ sku.categoryName }}
          </div>
          <StatusChip
            domain="generic"
            :value="sku.status"
          />
        </VCardText>
      </VCard>
      <VCard class="mb-4">
        <VCardItem>
          <VCardTitle>{{ t('catalog.costTimeline') }}</VCardTitle>
        </VCardItem>
        <VTable>
          <thead>
            <tr>
              <th>{{ t('catalog.validFrom') }}</th>
              <th>{{ t('catalog.validTo') }}</th>
              <th class="text-end">
                {{ t('catalog.unitCost') }}
              </th>
              <th class="text-end">
                {{ t('catalog.freight') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="cost in sku.costs"
              :key="cost.id"
            >
              <td>{{ cost.validFrom }}</td>
              <td>{{ cost.validTo || t('catalog.openEnded') }}</td>
              <td class="text-end">
                <MoneyText
                  :amount="cost.unitCost"
                  :currency="cost.currency"
                />
              </td>
              <td class="text-end">
                <MoneyText
                  :amount="cost.freight"
                  :currency="cost.currency"
                />
              </td>
            </tr>
          </tbody>
        </VTable>
      </VCard>
      <VCard class="mb-4">
        <VCardItem>
          <VCardTitle>{{ t('catalog.recentProfit') }}</VCardTitle>
          <VCardSubtitle>{{ t('common.fromSystem') }}</VCardSubtitle>
        </VCardItem>
        <VTable>
          <thead>
            <tr>
              <th>{{ t('common.period') }}</th>
              <th>{{ t('common.store') }}</th>
              <th class="text-end">
                {{ t('profit.profit') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in sku.profits.slice(0, 12)"
              :key="`${row.period}-${row.storeName}`"
            >
              <td>{{ row.period }}</td>
              <td>{{ row.storeName }}</td>
              <td class="text-end">
                <MoneyText
                  :amount="row.profit"
                  :currency="row.currency"
                />
              </td>
            </tr>
          </tbody>
        </VTable>
        <VCardText v-if="sku.profits.length === 0">
          <EmptyState />
        </VCardText>
      </VCard>
      <VCard>
        <VCardItem>
          <VCardTitle>{{ t('catalog.mappings') }}</VCardTitle>
        </VCardItem>
        <VTable>
          <thead>
            <tr>
              <th>{{ t('common.store') }}</th>
              <th>{{ t('catalog.platformSku') }}</th>
              <th>{{ t('common.status') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in sku.mappings"
              :key="row.id"
            >
              <td>{{ row.storeName }}</td>
              <td>{{ row.platformSku }}</td>
              <td>
                <StatusChip
                  domain="mapping"
                  :value="row.status"
                />
              </td>
            </tr>
          </tbody>
        </VTable>
      </VCard>
    </DetailPage>
    <FormDrawer
      v-model="open"
      :title="t('catalog.addCost')"
      :saving="saving"
      @save="saveCost"
    >
      <AppTextField
        v-model="form.validFrom"
        type="date"
        :label="t('catalog.validFrom')"
        :rules="[requiredText(t('catalog.validFrom'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.unitCost"
        :label="t('catalog.unitCost')"
        :rules="[requiredText(t('catalog.unitCost')), moneyText(t('catalog.unitCost'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.freightPerUnit"
        :label="t('catalog.freight')"
        :rules="[requiredText(t('catalog.freight')), moneyText(t('catalog.freight'))]"
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
