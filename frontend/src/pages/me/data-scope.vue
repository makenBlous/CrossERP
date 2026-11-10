<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { fetchScopedContext, fetchScopedEmployees, fetchScopedExpenses, fetchScopedOrders } from '@/api/scoped-reads'
import ScopedDataPreview from '@/components/biz/ScopedDataPreview.vue'
import DetailPage from '@/components/biz/DetailPage.vue'
import { useSessionStore } from '@/stores/session'

type TableKey = 'orders' | 'expenses' | 'employees'

const session = useSessionStore()
const orders = ref<Awaited<ReturnType<typeof fetchScopedOrders>>>([])
const expenses = ref<Awaited<ReturnType<typeof fetchScopedExpenses>>>([])
const employees = ref<Awaited<ReturnType<typeof fetchScopedEmployees>>>([])
const context = ref<Awaited<ReturnType<typeof fetchScopedContext>> | null>(null)
const loading = ref(false)
const tableErrors = ref<Partial<Record<TableKey, string>>>({})

async function load() {
  loading.value = true
  tableErrors.value = {}
  orders.value = []
  expenses.value = []
  employees.value = []
  context.value = null

  const [orderResult, expenseResult, employeeResult, contextResult] = await Promise.allSettled([
    fetchScopedOrders(),
    fetchScopedExpenses(),
    fetchScopedEmployees(),
    fetchScopedContext(),
  ])

  if (orderResult.status === 'fulfilled')
    orders.value = orderResult.value
  else
    tableErrors.value.orders = '当前主体无读取权限'

  if (expenseResult.status === 'fulfilled')
    expenses.value = expenseResult.value
  else
    tableErrors.value.expenses = '当前主体无读取权限'

  if (employeeResult.status === 'fulfilled')
    employees.value = employeeResult.value
  else
    tableErrors.value.employees = '当前主体无读取权限'

  if (contextResult.status === 'fulfilled')
    context.value = contextResult.value

  loading.value = false
}

watch(() => session.role, load)
onMounted(load)
</script>

<template>
  <DetailPage
    title="我的数据范围"
    subtitle="只展示当前登录主体按数据范围规则可读取的记录。"
  >
    <template #default>
      <ScopedDataPreview
        :orders="orders"
        :expenses="expenses"
        :employees="employees"
        :context="context"
        :subject-name="session.displayName"
        :subject-id="session.userId"
        :loading="loading"
        :table-errors="tableErrors"
        title="我的数据范围"
        subtitle="接口拒绝的表按空结果展示，权限规则保持不变。"
      />
    </template>
  </DetailPage>
</template>
