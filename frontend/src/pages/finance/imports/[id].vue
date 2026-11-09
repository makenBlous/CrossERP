/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchImport } from '@/api/finance'
import FinanceDetail from '@/views/finance/FinanceDetail.vue'

const route = useRoute(); const row = ref<NonNullable<Awaited<ReturnType<typeof fetchImport>>> | null>(null)

onMounted(async () => { row.value = await fetchImport(String((route.params as Record<string, string>).id)) })
</script>

<template>
  <FinanceDetail
    v-if="row"
    :title="row.fileName"
    :subtitle="`${row.connector} · ${row.importedAt}`"
    :status="row.status"
    domain="issue"
  >
    <VCard
      title="批次摘要"
      class="mb-6"
    >
      <VCardText>
        <VRow>
          <VCol cols="4">
            <div class="text-caption">
              总行数
            </div><div class="text-h5">
              {{ row.rows }}
            </div>
          </VCol><VCol cols="4">
            <div class="text-caption">
              错误行
            </div><div class="text-h5">
              {{ row.errors }}
            </div>
          </VCol><VCol cols="4">
            <div class="text-caption">
              失败原因
            </div><div class="text-body-1">
              {{ row.failure || '—' }}
            </div>
          </VCol>
        </VRow>
      </VCardText>
    </VCard><VCard title="原始行抽样">
      <VCardText>
        <VBtn
          to="/finance/rows/raw/row-42"
          variant="tonal"
          prepend-icon="tabler-file-search"
        >
          查看原始行
        </VBtn>
      </VCardText>
    </VCard>
  </FinanceDetail><EmptyState v-else />
</template>
