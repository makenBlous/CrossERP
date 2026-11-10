<script setup lang="ts">
import { draftVoucherReversal, fetchReversalCandidates } from '@/api/fin-gl'
import MoneyText from '@/components/biz/MoneyText.vue'
import StatusChip from '@/components/biz/StatusChip.vue'

const rows = ref<Awaited<ReturnType<typeof fetchReversalCandidates>>>([])
const error = ref('')
const message = ref('')
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    rows.value = await fetchReversalCandidates()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  }
  finally {
    loading.value = false
  }
}

async function reverse(id: string) {
  error.value = ''
  message.value = ''
  try {
    const row = await draftVoucherReversal(id)

    message.value = `${row.no} 已创建红字草稿，仍需另一人审批后过账。`
    await load()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : '冲销失败'
  }
}

onMounted(load)
</script>

<template>
  <ListPage
    storage-key="finance-reversals"
    title="红字冲销工作台"
    subtitle="已过账凭证不能编辑，只能全额借贷对调生成红字草稿。"
    :items="rows"
    :columns="[
      { key: 'no', title: '原凭证号' },
      { key: 'period', title: '期间' },
      { key: 'summary', title: '摘要' },
      { key: 'debit', title: '原借方', align: 'end' },
      { key: 'credit', title: '原贷方', align: 'end' },
      { key: 'reversalStatus', title: '冲销链' },
      { key: 'actions', title: '操作' },
    ]"
    :loading="loading"
    :error="error"
    @retry="load"
  >
    <template #actions>
      <VBtn
        variant="tonal"
        @click="load"
      >
        刷新
      </VBtn>
    </template>
    <template #widgets>
      <VAlert
        v-if="message"
        type="success"
        variant="tonal"
        class="mb-6"
      >
        {{ message }}
      </VAlert><VAlert
        type="info"
        variant="tonal"
        class="mb-6"
      >
        原凭证与红字凭证互相引用；一张原凭证只能有一张有效红字。金额由确定性 mock 服务复制，不由 AI 修改。
      </VAlert>
    </template>
    <template #item.debit="{ item }">
      <MoneyText
        :amount="item.debit"
        currency="CNY"
        minor
      />
    </template>
    <template #item.credit="{ item }">
      <MoneyText
        :amount="item.credit"
        currency="CNY"
        minor
      />
    </template>
    <template #item.reversalStatus="{ item }">
      <StatusChip
        domain="generic"
        :value="item.reversalStatus"
      />
    </template>
    <template #item.actions="{ item }">
      <VBtn
        v-if="item.canReverse"
        size="small"
        variant="tonal"
        data-test="reverse-draft"
        @click.stop="reverse(item.id)"
      >
        生成红字草稿
      </VBtn><VChip
        v-else
        size="small"
        :color="item.reversedByVoucherId ? 'success' : 'info'"
      >
        {{ item.reversedByVoucherId ? '已生成' : '红字草稿' }}
      </VChip>
    </template>
  </ListPage>
</template>
