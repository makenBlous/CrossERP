<script setup lang="ts">
import { createPurchaseOrder, fetchSupplyLookups } from '@/api/procurement'
import type { SupplyLookups } from '@/types/domain'
import { moneyText, numberText, requiredText } from '@core/utils/validators'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const lookups = ref<SupplyLookups | null>(null)
const step = ref(0)
const saving = ref(false)
const error = ref('')

const form = reactive({
  supplierId: '',
  expectedAt: '2026-11-20',
})

const lines = ref([{ internalSku: '', qty: '10', unitCost: '20.0000' }])

const steps = computed(() => [
  { title: t('procurement.wizardSupplier'), icon: 'tabler-building-factory' },
  { title: t('procurement.wizardItems'), icon: 'tabler-packages' },
  { title: t('procurement.wizardDue'), icon: 'tabler-calendar' },
])

onMounted(async () => {
  lookups.value = await fetchSupplyLookups()
  form.supplierId = lookups.value.suppliers[0]?.id ?? ''
  lines.value[0].internalSku = lookups.value.skus[0]?.id ?? ''
})

function addLine() {
  lines.value.push({
    internalSku: lookups.value?.skus[0]?.id ?? '',
    qty: '10',
    unitCost: '20.0000',
  })
}

function removeLine(index: number) {
  if (lines.value.length === 1)
    return

  lines.value.splice(index, 1)
}

async function persist(submit: boolean) {
  saving.value = true
  error.value = ''
  try {
    const created = await createPurchaseOrder({
      supplierId: form.supplierId,
      expectedAt: form.expectedAt,
      submit,
      lines: lines.value.map(line => ({
        internalSku: line.internalSku,
        qty: Number.parseInt(line.qty, 10),
        unitCost: line.unitCost,
      })),
    })

    await router.push({ path: `/procurement/orders/${created.id}` })
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
  <!-- 分步结构改编自 Vuexy form-wizard-numbered / AppStepper。三步字段都留在页面上，方便填写和测试。 -->
  <div>
    <div class="d-flex flex-wrap justify-space-between gap-4 mb-6">
      <div>
        <h4 class="text-h4">
          {{ t('procurement.newOrder') }}
        </h4>
        <div class="text-body-1">
          {{ t('procurement.ordersSubtitle') }}
        </div>
      </div>
      <div class="d-flex gap-4">
        <VBtn
          variant="tonal"
          color="secondary"
          :to="{ path: '/procurement/orders' }"
        >
          {{ t('foundation.cancel') }}
        </VBtn>
        <VBtn
          data-test="po-save"
          :loading="saving"
          variant="tonal"
          @click="persist(false)"
        >
          {{ t('procurement.saveDraft') }}
        </VBtn>
        <VBtn
          data-test="po-submit"
          :loading="saving"
          @click="persist(true)"
        >
          {{ t('procurement.submit') }}
        </VBtn>
      </div>
    </div>
    <VAlert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-4"
    >
      {{ error }}
    </VAlert>
    <VCard class="mb-6">
      <VCardText>
        <AppStepper
          v-model:current-step="step"
          :items="steps"
          align="start"
        />
      </VCardText>
    </VCard>
    <VForm @submit.prevent="persist(false)">
      <VWindow
        v-model="step"
        class="disable-tab-transition"
        :touch="false"
      >
        <VWindowItem>
          <VCard :title="t('procurement.wizardSupplier')">
            <VCardText>
              <AppSelect
                v-model="form.supplierId"
                :items="(lookups?.suppliers ?? []).map(item => ({ title: item.label, value: item.id }))"
                :label="t('procurement.supplier')"
                :rules="[requiredText(t('procurement.supplier'))]"
              />
            </VCardText>
          </VCard>
        </VWindowItem>
        <VWindowItem>
          <VCard :title="t('procurement.wizardItems')">
            <VCardText>
              <div
                v-for="(line, index) in lines"
                :key="index"
                class="d-flex flex-wrap gap-4 mb-4"
              >
                <AppSelect
                  v-model="line.internalSku"
                  :items="(lookups?.skus ?? []).map(item => ({ title: item.label, value: item.id }))"
                  :label="t('inventory.sku')"
                  :rules="[requiredText(t('inventory.sku'))]"
                  style="min-width: 240px"
                />
                <AppTextField
                  v-model="line.qty"
                  :label="t('inventory.qty')"
                  :rules="[requiredText(t('inventory.qty')), numberText(t('inventory.qty'))]"
                  style="max-width: 120px"
                />
                <AppTextField
                  v-model="line.unitCost"
                  :label="t('procurement.unitCost')"
                  :rules="[requiredText(t('procurement.unitCost')), moneyText(t('procurement.unitCost'))]"
                  style="max-width: 160px"
                />
                <VBtn
                  variant="text"
                  color="error"
                  @click="removeLine(index)"
                >
                  {{ t('procurement.removeLine') }}
                </VBtn>
              </div>
              <VBtn
                variant="tonal"
                @click="addLine"
              >
                {{ t('procurement.addLine') }}
              </VBtn>
            </VCardText>
          </VCard>
        </VWindowItem>
        <VWindowItem>
          <VCard :title="t('procurement.wizardDue')">
            <VCardText>
              <AppTextField
                v-model="form.expectedAt"
                type="date"
                :label="t('procurement.due')"
                :rules="[requiredText(t('procurement.due'))]"
              />
            </VCardText>
          </VCard>
        </VWindowItem>
      </VWindow>
      <div class="d-flex justify-space-between mt-6">
        <VBtn
          variant="tonal"
          :disabled="step === 0"
          @click="step -= 1"
        >
          {{ t('procurement.back') }}
        </VBtn>
        <VBtn
          v-if="step < 2"
          @click="step += 1"
        >
          {{ t('procurement.next') }}
        </VBtn>
      </div>
    </VForm>
  </div>
</template>
