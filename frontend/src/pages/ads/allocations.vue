<script setup lang="ts">
import { fetchAdCampaigns, fetchAllocations, saveAdAllocation } from '@/api/ads'
import { fetchProfit } from '@/api/finance'
import MoneyText from '@/components/biz/MoneyText.vue'
import FinanceTablePage, { type FinanceRow } from '@/views/finance/FinanceTablePage.vue'

type AllocationRows = Awaited<ReturnType<typeof fetchAllocations>>

const rows = ref<AllocationRows>([])
const campaigns = ref<Awaited<ReturnType<typeof fetchAdCampaigns>>>([])
const skus = ref<string[]>([])
const campaignId = ref('')
const shares = ref<Array<{ sku: string; ratio: number }>>([])
const error = ref('')
const message = ref('')

const campaignName = computed(() => campaigns.value.find(item => item.id === campaignId.value)?.name ?? '')

// 比例合计只是整数百分比计数，用来提示用户；金额分摊全部在服务层完成。
const ratioTotal = computed(() => shares.value.reduce((sum, item) => sum + (Number(item.ratio) || 0), 0))

function loadShares() {
  const existing = rows.value.filter(row => row.campaign === campaignName.value)

  shares.value = existing.length
    ? existing.map(row => ({ sku: row.sku, ratio: row.ratio }))
    : [{ sku: skus.value[0] ?? '', ratio: 100 }]
}

onMounted(async () => {
  const [allocationRows, campaignRows, profit] = await Promise.all([fetchAllocations(), fetchAdCampaigns(), fetchProfit()])

  rows.value = allocationRows
  campaigns.value = campaignRows
  skus.value = [...new Set(profit.rows.map(row => row.sku))]
  campaignId.value = campaignRows[0]?.id ?? ''
  loadShares()
})

watch(campaignId, loadShares)

function addShare() {
  shares.value = [...shares.value, { sku: skus.value.find(sku => !shares.value.some(item => item.sku === sku)) ?? '', ratio: 0 }]
}

function removeShare(index: number) {
  shares.value = shares.value.filter((_, i) => i !== index)
}

const columns = [{ key: 'campaign', title: '活动' }, { key: 'sku', title: '内部 SKU' }, { key: 'ratio', title: '比例 %' }, { key: 'spendDisplay', title: '分摊花费' }, { key: 'source', title: '来源' }]

async function save() {
  error.value = ''
  message.value = ''

  const result = await saveAdAllocation(campaignId.value, shares.value.map(item => ({ sku: item.sku, ratio: Number(item.ratio) })))

  if (result) {
    rows.value = result
    message.value = `已保存 ${campaignName.value} 的分摊规则，SKU 广告成本已由服务层重算。`
  }
  else {
    error.value = '比例必须为正整数、SKU 不能重复，且同一活动的比例合计必须恰好为 100%。'
  }
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        广告费分摊
      </h4>
      <p class="text-body-1 text-medium-emphasis mb-0">
        按活动设置完整的 SKU 分摊规则，保存后由代码重算每个 SKU 的广告成本。
      </p>
    </div>
    <VCard class="mb-6">
      <VCardText>
        <VRow>
          <VCol
            cols="12"
            md="5"
          >
            <AppSelect
              v-model="campaignId"
              :items="campaigns.map(item => ({ title: item.name, value: item.id }))"
              label="广告活动"
            />
          </VCol>
        </VRow>
        <VRow
          v-for="(share, index) in shares"
          :key="index"
          class="align-end"
        >
          <VCol
            cols="12"
            md="5"
          >
            <AppSelect
              v-model="share.sku"
              :items="skus"
              label="内部 SKU"
            />
          </VCol>
          <VCol
            cols="8"
            md="3"
          >
            <AppTextField
              v-model.number="share.ratio"
              type="number"
              label="分摊比例 %"
            />
          </VCol>
          <VCol
            cols="4"
            md="2"
          >
            <VBtn
              variant="text"
              color="error"
              prepend-icon="tabler-trash"
              :disabled="shares.length <= 1"
              @click="removeShare(index)"
            >
              移除
            </VBtn>
          </VCol>
        </VRow>
        <div class="d-flex flex-wrap align-center gap-4 mt-4">
          <VBtn
            variant="tonal"
            prepend-icon="tabler-plus"
            @click="addShare"
          >
            添加 SKU
          </VBtn>
          <VChip
            :color="ratioTotal === 100 ? 'success' : 'warning'"
            label
          >
            比例合计 {{ ratioTotal }}%
          </VChip>
          <VBtn @click="save">
            保存分摊规则
          </VBtn>
        </div>
        <VAlert
          type="info"
          variant="tonal"
          class="mt-4"
        >
          广告金额只由服务层计算，页面不做金额运算。保存会替换该活动原有的分摊规则。
        </VAlert>
        <VAlert
          v-if="message"
          type="success"
          variant="tonal"
          class="mt-4"
        >
          {{ message }}
        </VAlert>
        <VAlert
          v-if="error"
          type="error"
          variant="tonal"
          class="mt-4"
        >
          {{ error }}
        </VAlert>
      </VCardText>
    </VCard>
    <FinanceTablePage
      storage-key="ads-allocations"
      title="分摊结果"
      :rows="rows as unknown as FinanceRow[]"
      :columns="columns"
    >
      <template #item.spendDisplay="{ item }">
        <MoneyText
          :amount="Number(item.spend)"
          :currency="item.currency as any"
          minor
        />
      </template>
    </FinanceTablePage>
  </div>
</template>
