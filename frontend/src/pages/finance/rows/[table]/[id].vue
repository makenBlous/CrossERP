<script setup lang="ts">
import { fetchSourceRow } from '@/api/finance'
import FinanceDetail from '@/views/finance/FinanceDetail.vue'

const route = useRoute()
const row = ref<NonNullable<Awaited<ReturnType<typeof fetchSourceRow>>> | null>(null)

onMounted(async () => {
  const params = route.params as Record<string, string>

  row.value = await fetchSourceRow(String(params.table), String(params.id))
})
</script>

<template>
  <FinanceDetail
    v-if="row"
    :title="`原始行 ${row.id}`"
    :subtitle="`${row.table} · ${row.sourceFile} · 第 ${row.rowNo} 行`"
  >
    <VCard
      title="字段对照"
      class="mb-6"
    >
      <VTable>
        <tbody>
          <tr
            v-for="(value, key) in row.payload"
            :key="key"
          >
            <td>{{ key }}</td><td class="font-weight-medium">
              {{ value }}
            </td>
          </tr>
        </tbody>
      </VTable>
    </VCard><VCard title="JSON 原文">
      <VCardText><pre class="text-body-2">{{ JSON.stringify(row.payload, null, 2) }}</pre></VCardText>
    </VCard>
  </FinanceDetail>
  <EmptyState
    v-else
    title="未找到原始行"
    back-to="/finance/imports"
  />
</template>
