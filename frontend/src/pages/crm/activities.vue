<script setup lang="ts">
import { fetchCrmActivities } from '@/api/crm'
import ListPage from '@/components/biz/ListPage.vue'

const rows = ref<Array<{ id: string
  [key: string]: unknown }>>([])

onMounted(async () => {
  rows.value = await fetchCrmActivities()
})

const columns = [{ key: 'at', title: '时间' }, { key: 'kind', title: '类型' }, { key: 'subject', title: '主题' }, { key: 'owner', title: '负责人' }, { key: 'status', title: '状态' }]
</script>

<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h4 class="text-h4">
          跟进日历
        </h4><p class="text-body-1 mb-0">
          电话、邮件和会议安排
        </p>
      </div><VBtn
        color="primary"
        prepend-icon="tabler-plus"
      >
        新建跟进
      </VBtn>
    </div><VRow class="mb-6">
      <VCol
        cols="12"
        md="8"
      >
        <VCard title="2026 年 11 月">
          <VCardText>
            <VCalendar
              color="primary"
              :events="rows.map(row => ({ title: row.subject, start: String(row.at).slice(0, 10), color: row.status === 'done' ? 'success' : 'primary' }))"
            />
          </VCardText>
        </VCard>
      </VCol><VCol
        cols="12"
        md="4"
      >
        <VCard title="今日摘要">
          <VCardText>
            <div class="text-h3">
              {{ rows.filter(row => String(row.at).startsWith('2026-11-12')).length }}
            </div><div class="text-body-2">
              项待跟进
            </div>
          </VCardText>
        </VCard>
      </VCol>
    </VRow><ListPage
      storage-key="crm-activities"
      title="跟进记录"
      :items="rows"
      :columns="columns"
    />
  </div>
</template>
