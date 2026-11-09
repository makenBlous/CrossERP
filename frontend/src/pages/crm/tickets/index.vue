<script setup lang="ts">
import { createCrmTicket, fetchAccounts, fetchCrmTickets } from '@/api/crm'
import { fetchOrders } from '@/api/orders'
import ListPage from '@/components/biz/ListPage.vue'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'

const router = useRouter()

const rows = ref<Array<{ id: string
  [key: string]: unknown }>>([])

const accounts = ref<{ id: string
  name: string }[]>([])

const orders = ref<{ id: string
  orderNo: string }[]>([])

const open = ref(false)
const form = reactive({ accountId: '', orderNo: '', subject: '' })

async function load() {
  rows.value = await fetchCrmTickets()
  accounts.value = (await fetchAccounts()).map(item => ({ id: item.id, name: item.name }))
  orders.value = (await fetchOrders()).map(item => ({ id: item.id, orderNo: item.orderNo }))
}

onMounted(load)

async function save() {
  await createCrmTicket({ accountId: form.accountId, orderNo: form.orderNo || null, subject: form.subject })
  open.value = false
  form.subject = ''
  form.orderNo = ''
  await load()
}
const columns = [{ key: 'subject', title: '主题' }, { key: 'accountId', title: '客户' }, { key: 'orderNo', title: '关联订单' }, { key: 'status', title: '状态' }]
</script>

<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h4 class="text-h4">
          售后工单
        </h4><p class="text-body-1 mb-0">
          平台或独立站售后，关联订单可追溯。
        </p>
      </div><PermissionGate action="create">
        <VBtn
          color="primary"
          prepend-icon="tabler-plus"
          @click="open = true"
        >
          新建工单
        </VBtn>
      </PermissionGate>
    </div><ListPage
      storage-key="crm-tickets"
      title="工单列表"
      :items="rows"
      :columns="columns"
      @open="router.push(`/crm/tickets/${$event.id}`)"
    >
      <template #item.status="{ item }">
        <StatusChip
          domain="generic"
          :value="String(item.status)"
        />
      </template>
    </ListPage><FormDrawer
      v-model="open"
      title="新建售后工单"
      @save="save"
    >
      <AppSelect
        v-model="form.accountId"
        label="客户"
        :items="accounts.map(item => ({ title: item.name, value: item.id }))"
      /><AppTextField
        v-model="form.orderNo"
        label="关联订单（可选）"
        :items="orders.map(item => ({ title: item.orderNo, value: item.orderNo }))"
      /><AppTextField
        v-model="form.subject"
        label="问题主题"
      />
    </FormDrawer>
  </div>
</template>
