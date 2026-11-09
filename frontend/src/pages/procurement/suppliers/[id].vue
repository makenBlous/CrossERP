<script setup lang="ts">
import { fetchSupplier, updateSupplier } from '@/api/procurement'
import DetailPage from '@/components/biz/DetailPage.vue'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import { usePageContext } from '@/composables/usePageContext'
import type { CurrencyCode, SupplierDetailView } from '@/types/domain'
import { requiredText } from '@core/utils/validators'
import { readParam } from '@/utils/route-param'

const route = useRoute()
const { t } = useI18n({ useScope: 'global' })
const { setSelected } = usePageContext()
const supplier = ref<SupplierDetailView | null>(null)
const loaded = ref(false)
const error = ref('')
const tab = ref('profile')
const open = ref(false)
const saving = ref(false)

const form = reactive({
  name: '',
  country: '',
  currency: 'CNY' as CurrencyCode,
  remark: '',
  contactName: '',
  email: '',
  phone: '',
})

const supplierId = computed(() => readParam(route.params, 'id'))
const currencies = ['USD', 'CNY', 'EUR', 'GBP', 'JPY'].map(item => ({ title: item, value: item }))

async function load() {
  loaded.value = false
  error.value = ''
  try {
    supplier.value = await fetchSupplier(supplierId.value)
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loaded.value = true
  }
}

onMounted(load)
watch(supplierId, load)
watch(supplier, value => setSelected(value?.id ?? null))
onUnmounted(() => setSelected(null))

const tabs = computed(() => [
  { value: 'profile', title: t('procurement.profile'), icon: 'tabler-building' },
  { value: 'orders', title: t('procurement.purchases'), icon: 'tabler-file-invoice' },
  { value: 'ap', title: t('procurement.apBalance'), icon: 'tabler-cash' },
])

function startEdit() {
  if (!supplier.value)
    return

  const contact = supplier.value.contacts[0]

  form.name = supplier.value.name
  form.country = supplier.value.country
  form.currency = supplier.value.currency
  form.remark = supplier.value.remark
  form.contactName = contact?.name ?? ''
  form.email = contact?.email ?? ''
  form.phone = contact?.phone ?? ''
  open.value = true
}

async function save() {
  if (!supplier.value)
    return

  saving.value = true
  error.value = ''
  try {
    await updateSupplier(supplier.value.id, { ...form })
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
      :to="{ path: '/procurement/suppliers' }"
    >
      {{ t('procurement.suppliersTitle') }}
    </VBtn>
    <ErrorState
      v-if="error"
      class="mb-4"
      :text="error"
      @retry="load"
    />
    <LoadingState v-if="!loaded" />
    <VAlert
      v-else-if="!supplier"
      type="warning"
      variant="tonal"
    >
      {{ t('procurement.supplierMissing') }}
    </VAlert>
    <DetailPage
      v-else
      :title="supplier.name"
      :subtitle="`${supplier.country} · ${supplier.currency}`"
      domain="supplier"
      :status="supplier.status"
      :timeline="supplier.timeline"
    >
      <template #actions>
        <PermissionGate action="update">
          <VBtn
            variant="tonal"
            @click="startEdit"
          >
            {{ t('procurement.editSupplier') }}
          </VBtn>
        </PermissionGate>
      </template>
      <VTabs
        v-model="tab"
        class="v-tabs-pill mb-6"
      >
        <VTab
          v-for="item in tabs"
          :key="item.value"
          :value="item.value"
        >
          <VIcon
            :size="18"
            :icon="item.icon"
            class="me-1"
          />
          <span>{{ item.title }}</span>
        </VTab>
      </VTabs>
      <VWindow
        v-model="tab"
        class="disable-tab-transition"
        :touch="false"
      >
        <VWindowItem value="profile">
          <VCard>
            <VCardText>
              <div class="mb-2">
                {{ supplier.remark }}
              </div>
              <div
                v-for="contact in supplier.contacts"
                :key="contact.id"
              >
                {{ contact.name }} · {{ contact.email }} · {{ contact.phone }}
              </div>
            </VCardText>
          </VCard>
        </VWindowItem>
        <VWindowItem value="orders">
          <VCard>
            <VTable>
              <thead>
                <tr>
                  <th>{{ t('inventory.docNo') }}</th>
                  <th>{{ t('common.status') }}</th>
                  <th>{{ t('procurement.due') }}</th>
                  <th class="text-end">
                    {{ t('procurement.amount') }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="order in supplier.orders"
                  :key="order.id"
                >
                  <td>
                    <RouterLink :to="{ path: `/procurement/orders/${order.id}` }">
                      {{ order.no }}
                    </RouterLink>
                  </td>
                  <td>
                    <StatusChip
                      domain="purchase_order"
                      :value="order.status"
                    />
                  </td>
                  <td>{{ order.expectedAt }}</td>
                  <td class="text-end">
                    <MoneyText
                      :amount="order.amount"
                      :currency="order.currency"
                    />
                  </td>
                </tr>
              </tbody>
            </VTable>
          </VCard>
        </VWindowItem>
        <VWindowItem value="ap">
          <VCard>
            <VCardText>
              <div class="text-h5 mb-2">
                <MoneyText
                  :amount="supplier.apBalance"
                  :currency="supplier.apCurrency"
                />
              </div>
              <p class="mb-0">
                {{ t('procurement.apHint') }}
              </p>
            </VCardText>
          </VCard>
        </VWindowItem>
      </VWindow>
    </DetailPage>
    <FormDrawer
      v-model="open"
      :title="t('procurement.editSupplier')"
      :saving="saving"
      @save="save"
    >
      <AppTextField
        v-model="form.name"
        :label="t('procurement.supplier')"
        :rules="[requiredText(t('procurement.supplier'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.country"
        :label="t('inventory.country')"
        class="mb-4"
      />
      <AppSelect
        v-model="form.currency"
        :items="currencies"
        :label="t('procurement.currency')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.contactName"
        :label="t('procurement.contact')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.email"
        :label="t('procurement.email')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.phone"
        :label="t('procurement.phone')"
        class="mb-4"
      />
      <AppTextField
        v-model="form.remark"
        :label="t('procurement.remark')"
      />
    </FormDrawer>
  </div>
</template>
