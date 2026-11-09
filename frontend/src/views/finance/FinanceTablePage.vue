<script setup lang="ts">
import ListPage from '@/components/biz/ListPage.vue'

export interface FinanceRow { id: string; [key: string]: unknown }
export interface FinanceColumn { key: string; title: string; align?: 'start' | 'end' | 'center' }

const props = withDefaults(defineProps<{
  storageKey: string
  title: string
  subtitle?: string
  rows: FinanceRow[]
  columns: FinanceColumn[]
  detailBase?: string
  notice?: string
}>(), { subtitle: '', detailBase: '', notice: '' })

const router = useRouter()

const domainByStorage: Record<string, 'import_batch' | 'settlement' | 'recon_run' | 'fee_map' | 'column_map' | 'export_artifact' | 'clearing' | 'ad_campaign' | 'ad_import' | 'allocation' | 'ar_item' | 'ap_item' | 'generic'> = {
  'finance-imports': 'import_batch',
  'finance-settlements': 'settlement',
  'finance-recon': 'recon_run',
  'finance-fee-map': 'fee_map',
  'finance-column-maps': 'column_map',
  'finance-exports': 'export_artifact',
  'finance-clearing': 'clearing',
  'ads-campaigns': 'ad_campaign',
  'ads-imports': 'ad_import',
  'ads-allocations': 'allocation',
  'finance-ar': 'ar_item',
  'finance-ap': 'ap_item',
}

const statusDomain = computed(() => domainByStorage[props.storageKey] ?? 'generic')

function statusKey(key: string) {
  return key === 'status' || key.endsWith('Status')
}

function amountKey(key: string) {
  return /amount|spend|sales|total|difference|debit|credit/i.test(key)
}

const summary = computed(() => {
  const amount = props.rows.reduce((sum, row) => {
    const values = Object.entries(row as Record<string, unknown>)
    const found = values.find(([key, value]) => amountKey(key) && typeof value === 'number')

    return sum + (typeof found?.[1] === 'number' ? Number(found[1]) : 0)
  }, 0)

  return { count: props.rows.length, amount: amount.toLocaleString() }
})

function open(row: FinanceRow) {
  if (props.detailBase)
    router.push(`${props.detailBase}/${row.id}`)
}
</script>

<template>
  <div>
    <VAlert
      v-if="notice"
      type="info"
      variant="tonal"
      class="mb-6"
    >
      {{ notice }}
    </VAlert>
    <ListPage
      :storage-key="storageKey"
      :title="title"
      :subtitle="subtitle"
      :items="rows"
      :columns="columns"
      @open="open"
    >
      <template #widgets>
        <VRow class="mb-6">
          <VCol
            cols="12"
            sm="4"
          >
            <KpiCard
              title="记录数"
              :value="String(summary.count)"
              icon="tabler-list-details"
              color="primary"
            />
          </VCol>
          <VCol
            cols="12"
            sm="4"
          >
            <KpiCard
              title="金额/花费"
              :value="summary.amount"
              icon="tabler-cash"
              color="success"
              hint="服务层已存储结果"
            />
          </VCol>
          <VCol
            cols="12"
            sm="4"
          >
            <KpiCard
              title="异常/待处理"
              :value="String(rows.filter(row => ['failed', 'open', 'unmapped', 'pending'].includes(String(row.status))).length)"
              icon="tabler-alert-triangle"
              color="warning"
            />
          </VCol>
        </VRow>
      </template>
      <template
        v-for="column in columns"
        #[`item.${column.key}`]="{ item }"
        :key="column.key"
      >
        <slot
          :name="`item.${column.key}`"
          :item="item"
        >
          <StatusChip
            v-if="statusKey(column.key)"
            :domain="statusDomain"
            :value="String(item[column.key] ?? '')"
          />
          <span v-else>{{ item[column.key] ?? '—' }}</span>
        </slot>
      </template>
    </ListPage>
  </div>
</template>
