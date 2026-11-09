<script setup lang="ts">
import { fetchSettlement } from '@/api/finance'
import MoneyText from '@/components/biz/MoneyText.vue'
import FinanceDetail from '@/views/finance/FinanceDetail.vue'

const route = useRoute()
const row = ref<NonNullable<Awaited<ReturnType<typeof fetchSettlement>>> | null>(null)

onMounted(async () => {
  row.value = await fetchSettlement(String((route.params as Record<string, string>).id))
})
</script>

<template>
  <FinanceDetail
    v-if="row"
    :title="row.externalId"
    :subtitle="`${row.storeName} · ${row.periodStart} ~ ${row.periodEnd}`"
  >
    <VCard
      title="结算头信息"
      class="mb-6"
    >
      <VCardText>
        <VRow>
          <VCol cols="4">
            <div class="text-caption">
              平台
            </div><div>{{ row.platform }}</div>
          </VCol><VCol cols="4">
            <div class="text-caption">
              币种
            </div><div>{{ row.currency }}</div>
          </VCol><VCol cols="4">
            <div class="text-caption">
              总额
            </div><div class="text-h5">
              <MoneyText
                :amount="row.total"
                :currency="row.currency"
                minor
              />
            </div>
          </VCol>
        </VRow>
      </VCardText>
    </VCard><VCard title="明细与费用分类">
      <VTable>
        <thead>
          <tr>
            <th>类型</th><th>描述</th><th class="text-end">
              金额
            </th>
          </tr>
        </thead><tbody>
          <tr
            v-for="line in row.lines"
            :key="line.id"
          >
            <td>{{ line.type }}</td><td><span>{{ line.description }}</span> <RouterLink :to="`/finance/rows/settlement/${row.rawRowId}`" class="text-primary text-caption">原始行</RouterLink></td><td class="text-end">
              <MoneyText
                :amount="line.amount"
                :currency="row.currency"
                minor
              />
            </td>
          </tr>
        </tbody>
      </VTable>
    </VCard>
  </FinanceDetail>
  <EmptyState
    v-else
    title="未找到结算"
    back-to="/finance/settlements"
  />
</template>
