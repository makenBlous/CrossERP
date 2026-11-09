<script setup lang="ts">
import { fetchClearing, submitClearingApproval } from '@/api/finance'
import MoneyText from '@/components/biz/MoneyText.vue'
import StatusChip from '@/components/biz/StatusChip.vue'

const rows = ref<Awaited<ReturnType<typeof fetchClearing>>>([])
const selected = ref<string[]>([])
const submitted = ref(false)
const error = ref('')

onMounted(async () => {
  rows.value = await fetchClearing()
})

const chosen = computed(() => rows.value.filter(row => selected.value.includes(row.id)))
const difference = computed(() => chosen.value.reduce((sum, row) => sum + row.payoutAmount - row.arAmount, 0))

async function submit() {
  error.value = ''
  if (!selected.value.length) {
    error.value = '请至少选择一条打款与应收候选。'

    return
  }
  if (difference.value !== 0) {
    error.value = '所选打款与应收金额不相等，请调整选择。'

    return
  }
  const approval = await submitClearingApproval(selected.value)
  if (!approval) {
    error.value = '服务层校验未通过，未创建审批。'

    return
  }
  submitted.value = true
  rows.value = await fetchClearing()
}
</script>

<template>
  <div>
    <div class="d-flex justify-space-between align-center flex-wrap gap-4 mb-6">
      <div>
        <h4 class="text-h4">
          收付款核销
        </h4>
        <p class="text-body-1 text-medium-emphasis mb-0">
          选择多条打款和应收项目，服务层校验金额后提交审批。
        </p>
      </div>
      <VBtn
        prepend-icon="tabler-send"
        :disabled="difference !== 0 || !selected.length"
        @click="submit"
      >
        提交核销审批
      </VBtn>
    </div>
    <VAlert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-4"
    >
      {{ error }}
    </VAlert>
    <VAlert
      v-if="submitted"
      type="success"
      variant="tonal"
      class="mb-4"
    >
      核销申请已进入审批队列。
    </VAlert>
    <VRow>
      <VCol
        cols="12"
        md="7"
      >
        <VCard title="打款候选">
          <VTable>
            <thead><tr><th>选择</th><th>打款</th><th>金额</th><th>状态</th></tr></thead>
            <tbody>
              <tr
                v-for="row in rows"
                :key="row.id"
              >
                <td>
                  <VCheckbox
                    v-model="selected"
                    :value="row.id"
                    hide-details
                    density="compact"
                  />
                </td>
                <td>{{ row.payout }}</td>
                <td>
                  <MoneyText
                    :amount="row.payoutAmount"
                    :currency="row.currency"
                  />
                </td>
                <td>
                  <StatusChip
                    domain="clearing"
                    :value="row.status"
                  />
                </td>
              </tr>
            </tbody>
          </VTable>
        </VCard>
      </VCol>
      <VCol
        cols="12"
        md="5"
      >
        <VCard title="应收候选">
          <VList>
            <VListItem
              v-for="row in chosen"
              :key="row.id"
              :title="row.ar"
            >
              <template #append>
                <MoneyText
                  :amount="row.arAmount"
                  :currency="row.currency"
                />
              </template>
            </VListItem>
            <VListItem
              v-if="!chosen.length"
              title="请选择左侧打款项目"
            />
          </VList>
        </VCard>
      </VCol>
    </VRow>
    <VCard class="mt-6">
      <VCardText class="d-flex justify-space-between align-center flex-wrap gap-3">
        <span>所选差额</span>
        <VChip :color="difference === 0 ? 'success' : 'error'">
          {{ difference === 0 ? '相等' : '存在差额' }}
        </VChip>
      </VCardText>
    </VCard>
  </div>
</template>
