/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchAllocations, saveAdAllocation } from '@/api/ads'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

const rows = ref<Awaited<ReturnType<typeof fetchAllocations>>>([]); const sku = ref(''); const ratio = ref(10)

onMounted(async () => { rows.value = await fetchAllocations() })

const columns = [{ key: 'campaign', title: '活动' }, { key: 'sku', title: '内部 SKU' }, { key: 'ratio', title: '比例 %' }, { key: 'spend', title: '分摊花费' }, { key: 'source', title: '来源' }]
async function save() {
  if (!sku.value)
    sku.value = rows.value[0]?.sku ?? ''; const row = await saveAdAllocation(sku.value, ratio.value); if (row)
    rows.value = [...rows.value.filter(item => item.id !== row.id), row]
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        广告费分摊
      </h4><p class="text-body-1 text-medium-emphasis mb-0">
        规则保存后由代码重算每个 SKU 的广告成本。
      </p>
    </div><VCard class="mb-6">
      <VCardText>
        <VRow>
          <VCol
            cols="12"
            md="5"
          >
            <AppTextField
              v-model="sku"
              label="内部 SKU"
              placeholder="例如 TENT-2P"
            />
          </VCol><VCol
            cols="12"
            md="3"
          >
            <AppTextField
              v-model.number="ratio"
              type="number"
              label="分摊比例 %"
            />
          </VCol><VCol
            cols="12"
            md="4"
            class="d-flex align-end"
          >
            <VBtn @click="save">
              保存分摊规则
            </VBtn>
          </VCol>
        </VRow><VAlert
          type="info"
          variant="tonal"
          class="mt-4"
        >
          广告金额只由服务层计算，页面不做金额运算。
        </VAlert>
      </VCardText>
    </VCard><FinanceTablePage
      storage-key="ads-allocations"
      title="分摊结果"
      :rows="rows as unknown as FinanceRow[]"
      :columns="columns"
    />
  </div>
</template>
