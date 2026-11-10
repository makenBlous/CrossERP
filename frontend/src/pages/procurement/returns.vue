<script setup lang="ts">
import { confirmPurchaseReturn, createPurchaseReturn, fetchPurchaseReturns, fetchSupplyLookups } from '@/api/procurement'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import RecordDrawer from '@/components/biz/RecordDrawer.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useConfirm } from '@/composables/useConfirm'
import type { PurchaseReturnRow, SupplyLookups } from '@/types/domain'
import { moneyText, requiredText } from '@core/utils/validators'

const { t } = useI18n({ useScope: 'global' })
const { confirm } = useConfirm()
const rows = ref<PurchaseReturnRow[]>([])
const lookups = ref<SupplyLookups | null>(null)
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const drawer = ref(false)
const selected = ref<PurchaseReturnRow | null>(null)
const form = reactive({ supplierId: '', purchaseOrderId: '', amount: '100.0000' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await fetchPurchaseReturns()
    lookups.value = await fetchSupplyLookups()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loading.value = false
  }
}

onMounted(load)

const columns = computed(() => [
  { key: 'no', title: t('inventory.docNo') },
  { key: 'supplierName', title: t('procurement.supplier') },
  { key: 'purchaseOrderNo', title: t('procurement.ordersTitle') },
  { key: 'status', title: t('common.status') },
  { key: 'amount', title: t('procurement.amount'), align: 'end' as const },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [{
  key: 'status',
  label: t('common.status'),
  items: [...new Set(rows.value.map(item => item.status))].map(name => ({ title: name, value: name })),
}])

function startCreate() {
  form.supplierId = lookups.value?.suppliers[0]?.id ?? ''
  form.purchaseOrderId = lookups.value?.purchaseOrders[0]?.id ?? ''
  form.amount = '100.0000'
  open.value = true
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    await createPurchaseReturn({ ...form })
    open.value = false
    await load()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    saving.value = false
  }
}

async function confirmRow(row: PurchaseReturnRow) {
  const ok = await confirm({
    title: t('procurement.confirmReturn'),
    text: row.no,
    confirmText: t('procurement.confirmReturn'),
    cancelText: t('foundation.cancel'),
  })

  if (!ok)
    return

  try {
    await confirmPurchaseReturn(row.id)
    drawer.value = false
    await load()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}
</script>

<template>
  <div>
    <VAlert
      v-if="message"
      type="warning"
      variant="tonal"
      class="mb-4"
    >
      {{ message }}
    </VAlert>
    <ListPage
      storage-key="procurement-returns"
      :title="t('procurement.returnsTitle')"
      :subtitle="t('procurement.returnsSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      :loading="loading"
      :error="error"
      @retry="load"
      @open="row => { selected = row; drawer = true }"
    >
      <template #actions>
        <PermissionGate action="create">
          <VBtn
            color="primary"
            @click="startCreate"
          >
            {{ t('procurement.createReturn') }}
          </VBtn>
        </PermissionGate>
      </template>
      <template #item.status="{ item }">
        <StatusChip
          domain="purchase_return"
          :value="item.status"
        />
      </template>
      <template #item.amount="{ item }">
        <MoneyText
          :amount="item.amount"
          :currency="item.currency"
        />
      </template>
      <template #item.actions="{ item }">
        <VBtn
          size="small"
          variant="text"
          @click="selected = item; drawer = true"
        >
          {{ t('common.view') }}
        </VBtn>
        <PermissionGate action="update">
          <VBtn
            v-if="item.status === 'draft'"
            size="small"
            variant="text"
            data-test="confirm-purchase-return"
            @click="confirmRow(item)"
          >
            {{ t('procurement.confirmReturn') }}
          </VBtn>
        </PermissionGate>
      </template>
    </ListPage>
    <RecordDrawer
      v-model="drawer"
      :title="selected?.no || t('procurement.returnsTitle')"
    >
      <template v-if="selected">
        <p>{{ selected.supplierName }}</p>
        <p>{{ selected.purchaseOrderNo }}</p>
        <MoneyText
          :amount="selected.amount"
          :currency="selected.currency"
        />
        <VAlert
          type="info"
          variant="tonal"
          class="mt-4"
          data-test="purchase-return-lines"
        >
          <div class="font-weight-medium mb-2">退货明细（确认后写入负数库存流水）</div>
          <div
            v-for="line in selected.lines ?? []"
            :key="`${line.internalSku}-${line.batchNo}`"
          >
            {{ line.internalSku }} · {{ line.warehouseName }} · 批次 {{ line.batchNo }} · -{{ line.qty }} 件
          </div>
          <div class="mt-2">应付冲减：<MoneyText :amount="selected.payableReduction ?? selected.amount" :currency="selected.currency" /></div>
        </VAlert>
        <p class="mt-4">
          {{ t('procurement.returnsSubtitle') }}
        </p>
      </template>
    </RecordDrawer>
    <FormDrawer
      v-model="open"
      :title="t('procurement.createReturn')"
      :saving="saving"
      @save="save"
    >
      <AppSelect
        v-model="form.supplierId"
        :items="(lookups?.suppliers ?? []).map(item => ({ title: item.label, value: item.id }))"
        :label="t('procurement.supplier')"
        :rules="[requiredText(t('procurement.supplier'))]"
        class="mb-4"
      />
      <AppSelect
        v-model="form.purchaseOrderId"
        :items="(lookups?.purchaseOrders ?? []).map(item => ({ title: item.label, value: item.id }))"
        :label="t('procurement.ordersTitle')"
        :rules="[requiredText(t('procurement.ordersTitle'))]"
        class="mb-4"
      />
      <AppTextField
        v-model="form.amount"
        :label="t('procurement.amount')"
        :rules="[requiredText(t('procurement.amount')), moneyText(t('procurement.amount'))]"
      />
      <VAlert type="info" variant="tonal" class="mt-4">
        原型默认退货 5 件；金额由采购明细单价 × 数量确定性计算，提交人不能改写库存或应付。
      </VAlert>
    </FormDrawer>
  </div>
</template>
