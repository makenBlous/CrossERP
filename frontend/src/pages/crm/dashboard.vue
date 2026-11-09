<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchCrmDashboard } from '@/api/crm'
import KpiCard from '@/components/KpiCard.vue'

const data = ref<{ leads: number; openTickets: number; opportunities: number; pipeline: number } | null>(null)

onMounted(async () => { data.value = await fetchCrmDashboard() })
</script>

<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h4 class="text-h4">
          CRM 经营看板
        </h4><p class="text-body-1 mb-0">
          线索、商机和售后服务的统一视图
        </p>
      </div><VChip
        color="primary"
        variant="tonal"
      >
        2026 年 11 月
      </VChip>
    </div>
    <VRow>
      <VCol
        cols="12"
        sm="6"
        md="3"
      >
        <KpiCard
          title="有效线索"
          :value="String(data?.leads ?? 0)"
          hint="持续跟进"
          icon="tabler-user-plus"
        />
      </VCol><VCol
        cols="12"
        sm="6"
        md="3"
      >
        <KpiCard
          title="进行中商机"
          :value="String(data?.opportunities ?? 0)"
          hint="按阶段推进"
          icon="tabler-target"
        />
      </VCol><VCol
        cols="12"
        sm="6"
        md="3"
      >
        <KpiCard
          title="管道金额"
          :value="`${((data?.pipeline ?? 0) / 10000).toLocaleString()} USD`"
          hint="系统存储金额"
          icon="tabler-chart-dots"
        />
      </VCol><VCol
        cols="12"
        sm="6"
        md="3"
      >
        <KpiCard
          title="待处理工单"
          :value="String(data?.openTickets ?? 0)"
          hint="优先响应"
          icon="tabler-ticket"
        />
      </VCol>
    </VRow>
    <VRow class="mt-1">
      <VCol
        cols="12"
        md="8"
      >
        <VCard title="销售漏斗">
          <VCardText>
            <div class="d-flex flex-column gap-4">
              <div
                v-for="item in [['新线索', 68, 'primary'], ['已确认需求', 48, 'info'], ['已报价', 28, 'warning'], ['已转化', 16, 'success']]"
                :key="item[0]"
                class="d-flex align-center gap-4"
              >
                <span style="inline-size: 90px">{{ item[0] }}</span><VProgressLinear
                  :model-value="item[1] as number"
                  :color="item[2] as string"
                  height="12"
                  rounded
                /><span class="text-caption">{{ item[1] }}%</span>
              </div>
            </div>
          </VCardText>
        </VCard>
      </VCol><VCol
        cols="12"
        md="4"
      >
        <VCard title="本周行动">
          <VList>
            <VListItem
              prepend-icon="tabler-phone"
              title="联系 Summit Trail"
              subtitle="今天 10:00"
            /><VListItem
              prepend-icon="tabler-mail"
              title="发送 Ridge 报价"
              subtitle="明天 15:30"
            /><VListItem
              prepend-icon="tabler-calendar"
              title="德国客户回顾"
              subtitle="已完成"
            />
          </VList>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>
