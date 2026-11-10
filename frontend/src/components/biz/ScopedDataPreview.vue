<script setup lang="ts">
import type { ScopedContext } from '@/api/scoped-reads'
import type { ScopedEmployee, ScopedExpense, ScopedOrder } from '@/mocks/services/scoped-reads'

type ScopedTableKey = 'orders' | 'expenses' | 'employees'

interface Props {
  orders: ScopedOrder[]
  expenses: ScopedExpense[]
  employees: Array<Partial<ScopedEmployee>>
  context: ScopedContext | null
  subjectName: string
  subjectId: string
  loading?: boolean
  error?: string
  tableErrors?: Partial<Record<ScopedTableKey, string>>
  title?: string
  subtitle?: string
}

withDefaults(defineProps<Props>(), {
  loading: false,
  error: '',
  tableErrors: () => ({}),
  title: '当前身份可见数据预览',
  subtitle: '以下数据由当前会话身份调用 scoped read API 返回。',
})
</script>

<template>
  <VCard variant="outlined">
    <VCardItem>
      <VCardTitle>{{ title }}</VCardTitle>
      <VCardSubtitle>{{ subtitle }}</VCardSubtitle>
    </VCardItem>
    <VCardText>
      <VAlert
        v-if="error"
        type="error"
        variant="tonal"
        class="mb-4"
      >
        {{ error }}
      </VAlert>
      <VProgressLinear
        v-if="loading"
        indeterminate
        class="mb-4"
      />
      <div class="d-flex flex-wrap align-center gap-3 mb-4">
        <VChip
          color="primary"
          variant="tonal"
        >
          主体：{{ subjectName }}（{{ subjectId }}）
        </VChip>
        <StatusChip
          domain="generic"
          value="active"
        />
        <span v-if="context">数据范围：订单 {{ context.dataScopes.orders.join('、') || '无' }}；报销 {{ context.dataScopes.expenses.join('、') || '无' }}；员工档案 {{ context.dataScopes.employees.join('、') || '无' }}</span>
        <span v-else>数据范围：加载中</span>
        <span>绑定店铺：{{ context?.shopsForSubject.join('、') || '无' }}</span>
      </div>
      <VRow>
        <VCol
          cols="12"
          md="4"
        >
          <VCard variant="tonal">
            <VCardItem>
              <VCardTitle>订单</VCardTitle>
              <VCardSubtitle>{{ orders.length }} 条</VCardSubtitle>
            </VCardItem>
            <VAlert
              v-if="tableErrors?.orders"
              type="error"
              variant="tonal"
              class="mx-4 mb-4"
            >
              {{ tableErrors.orders }}
            </VAlert>
            <VTable
              data-testid="scope-preview-orders"
              density="compact"
            >
              <thead><tr><th>id</th><th>orderNo</th><th>shopId</th><th>ownerId</th><th>department</th></tr></thead>
              <tbody>
                <tr
                  v-for="item in orders"
                  :key="item.id"
                  :data-shop="item.shopId"
                  :data-owner="item.ownerId"
                >
                  <td>{{ item.id }}</td><td>{{ item.orderNo }}</td><td>{{ item.shopId }}</td><td>{{ item.ownerId }}</td><td>{{ item.department }}</td>
                </tr>
              </tbody>
            </VTable>
          </VCard>
        </VCol>
        <VCol
          cols="12"
          md="4"
        >
          <VCard variant="tonal">
            <VCardItem>
              <VCardTitle>报销</VCardTitle>
              <VCardSubtitle>{{ expenses.length }} 条</VCardSubtitle>
            </VCardItem>
            <VAlert
              v-if="tableErrors?.expenses"
              type="error"
              variant="tonal"
              class="mx-4 mb-4"
            >
              {{ tableErrors.expenses }}
            </VAlert>
            <VTable
              data-testid="scope-preview-expenses"
              density="compact"
            >
              <thead><tr><th>id</th><th>title</th><th>shopId</th><th>ownerId</th><th>department</th></tr></thead>
              <tbody>
                <tr
                  v-for="item in expenses"
                  :key="item.id"
                  :data-shop="item.shopId"
                  :data-owner="item.ownerId"
                >
                  <td>{{ item.id }}</td><td>{{ item.title }}</td><td>{{ item.shopId }}</td><td>{{ item.ownerId }}</td><td>{{ item.department }}</td>
                </tr>
              </tbody>
            </VTable>
          </VCard>
        </VCol>
        <VCol
          cols="12"
          md="4"
        >
          <VCard variant="tonal">
            <VCardItem>
              <VCardTitle>员工档案</VCardTitle>
              <VCardSubtitle>{{ employees.length }} 条</VCardSubtitle>
            </VCardItem>
            <VAlert
              v-if="tableErrors?.employees"
              type="error"
              variant="tonal"
              class="mx-4 mb-4"
            >
              {{ tableErrors.employees }}
            </VAlert>
            <VTable
              data-testid="scope-preview-employees"
              density="compact"
            >
              <thead><tr><th>id</th><th>name</th><th>shopId</th><th>ownerId</th><th>department</th></tr></thead>
              <tbody>
                <tr
                  v-for="item in employees"
                  :key="item.id"
                  :data-shop="item.shopId"
                  :data-owner="item.ownerId"
                >
                  <td>{{ item.id }}</td><td>{{ item.name }}</td><td>{{ item.shopId }}</td><td>{{ item.ownerId }}</td><td>{{ item.department }}</td>
                </tr>
              </tbody>
            </VTable>
          </VCard>
        </VCol>
      </VRow>
    </VCardText>
  </VCard>
</template>
