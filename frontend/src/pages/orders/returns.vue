<script setup lang="ts">
import { fetchOrders, fetchReturns } from '@/api/orders'
import { disposeSalesReturn, registerSalesReturn } from '@/api/workflows'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import ListPage from '@/components/biz/ListPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useConfirm } from '@/composables/useConfirm'
import { usePageContext } from '@/composables/usePageContext'
import { useSessionStore } from '@/stores/session'
import type { ReturnRow } from '@/types/domain'
import { can } from '@/utils/permission'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const session = useSessionStore()
const { confirm } = useConfirm()
const { setSelected } = usePageContext()
const rows = ref<ReturnRow[]>([])
const shippable = ref<Array<{ id: string; orderNo: string }>>([])
const loading = ref(true)
const error = ref('')
const message = ref('')
const open = ref(false)
const saving = ref(false)
const form = reactive({ orderId: '', disposition: 'restock' as 'restock' | 'scrap' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [returns, orders] = await Promise.all([fetchReturns(), fetchOrders()])

    rows.value = returns
    shippable.value = orders
      .filter(item => item.statusCode === 'shipped' || item.statusCode === 'partial_refund')
      .map(item => ({ id: item.id, orderNo: item.orderNo }))
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
  { key: 'orderNo', title: t('orders.orderNo') },
  { key: 'storeName', title: t('common.store') },
  { key: 'postedAt', title: t('orders.date') },
  { key: 'status', title: t('common.status') },
  { key: 'amount', title: t('common.amount'), align: 'end' as const },
  { key: 'actions', title: t('common.actions') },
])

const filters = computed(() => [
  { key: 'storeName', label: t('common.store'), items: [...new Set(rows.value.map(item => item.storeName))].map(name => ({ title: name, value: name })) },
  { key: 'status', label: t('common.status'), items: [...new Set(rows.value.map(item => item.status))].map(name => ({ title: name, value: name })) },
])

const batchActions = computed(() => {
  const actions = []

  if (can(session.role, 'receive'))
    actions.push({ key: 'restock', label: t('orders.restock') })

  if (can(session.role, 'update'))
    actions.push({ key: 'scrap', label: t('orders.scrap') })

  return actions
})

async function dispose(id: string, disposition: 'restock' | 'scrap') {
  const ok = await confirm({
    title: disposition === 'restock' ? t('orders.restock') : t('orders.scrap'),
    text: id,
    confirmText: disposition === 'restock' ? t('orders.restock') : t('orders.scrap'),
    cancelText: t('foundation.cancel'),
  })

  if (!ok)
    return

  message.value = ''
  try {
    await disposeSalesReturn(id, disposition)
    await load()
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}

async function onBatch(action: string, selected: ReturnRow[]) {
  const disposition = action === 'scrap' ? 'scrap' : 'restock'

  for (const row of selected.filter(item => item.status === 'posted')) {
    try {
      await disposeSalesReturn(row.id, disposition)
    }
    catch (err) {
      message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
    }
  }
  await load()
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    await registerSalesReturn(form.orderId, form.disposition)
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

function openRow(row: ReturnRow) {
  setSelected(row.orderId)
  router.push({ path: `/orders/${row.orderId}` })
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
      storage-key="order-returns"
      :title="t('orders.returnsTitle')"
      :subtitle="t('orders.returnsSubtitle')"
      :items="rows"
      :columns="columns"
      :filters="filters"
      date-key="postedAt"
      :loading="loading"
      :error="error"
      :batch-actions="batchActions"
      @retry="load"
      @open="openRow"
      @batch="onBatch"
    >
      <template #actions>
        <PermissionGate action="update">
          <VBtn
            color="primary"
            @click="open = true"
          >
            {{ t('orders.createReturn') }}
          </VBtn>
        </PermissionGate>
      </template>
      <template #item.status="{ item }">
        <StatusChip
          domain="return"
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
        <PermissionGate
          v-if="item.status === 'posted'"
          action="receive"
        >
          <VBtn
            size="small"
            variant="text"
            @click="dispose(item.id, 'restock')"
          >
            {{ t('orders.restock') }}
          </VBtn>
        </PermissionGate>
        <PermissionGate
          v-if="item.status === 'posted'"
          action="update"
        >
          <VBtn
            size="small"
            variant="text"
            @click="dispose(item.id, 'scrap')"
          >
            {{ t('orders.scrap') }}
          </VBtn>
        </PermissionGate>
        <VBtn
          size="small"
          variant="text"
          :to="{ path: `/orders/${item.orderId}` }"
        >
          {{ t('orders.openOrder') }}
        </VBtn>
      </template>
    </ListPage>
    <FormDrawer
      v-model="open"
      :title="t('orders.createReturn')"
      :saving="saving"
      @save="save"
    >
      <AppSelect
        v-model="form.orderId"
        :items="shippable.map(item => ({ title: item.orderNo, value: item.id }))"
        :label="t('orders.orderNo')"
        class="mb-4"
      />
      <AppSelect
        v-model="form.disposition"
        :items="[{ title: t('orders.restock'), value: 'restock' }, { title: t('orders.scrap'), value: 'scrap' }]"
        :label="t('common.status')"
      />
    </FormDrawer>
  </div>
</template>
