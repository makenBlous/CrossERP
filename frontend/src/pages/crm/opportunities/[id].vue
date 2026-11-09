<script setup lang="ts">
import { fetchOpportunity } from '@/api/crm'
import DetailPage from '@/components/biz/DetailPage.vue'
import MoneyText from '@/components/biz/MoneyText.vue'

const route = useRoute()
const router = useRouter()
const item = ref<any>(null)

onMounted(async () => {
  item.value = await fetchOpportunity(String((route.params as Record<string, unknown>).id))
})
</script>

<template>
  <DetailPage
    v-if="item"
    :title="item.name"
    :subtitle="item.accountName"
    domain="crm"
    :status="item.stage"
    :related="[{ id: item.accountId, type: '客户', label: item.accountName, to: `/crm/accounts/${item.accountId}` }]"
  >
    <VCard title="商机概览">
      <VCardText>
        <VRow>
          <VCol
            cols="12"
            md="6"
          >
            <div class="text-caption">
              阶段
            </div><VChip
              color="primary"
              variant="tonal"
            >
              {{ item.stage }}
            </VChip>
          </VCol><VCol
            cols="12"
            md="6"
          >
            <div class="text-caption">
              预计金额
            </div><MoneyText
              :amount="item.amount"
              :currency="item.currency"
            />
          </VCol>
        </VRow>
      </VCardText>
    </VCard><VCard
      class="mt-6"
      title="跟进计划"
    >
      <VCardText>
        <VTimeline density="compact">
          <VTimelineItem dot-color="primary">
            <div class="font-weight-medium">
              客户确认需求
            </div><div class="text-caption">
              下一步：发送样品和价格表
            </div>
          </VTimelineItem><VTimelineItem dot-color="info">
            <div class="font-weight-medium">
              建立商机
            </div><div class="text-caption">
              系统创建
            </div>
          </VTimelineItem>
        </VTimeline>
      </VCardText>
    </VCard><VBtn
      class="mt-4"
      variant="tonal"
      @click="router.push('/crm/opportunities')"
    >
      返回看板
    </VBtn>
  </DetailPage>
</template>
