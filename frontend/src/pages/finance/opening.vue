<script setup lang="ts">
import { activateOpeningBatch, balanceOpeningTrial, fetchOpening } from '@/api/fin-gl'
import MoneyText from '@/components/biz/MoneyText.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { canPermission } from '@/api/mock-client'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const opening = ref<Awaited<ReturnType<typeof fetchOpening>> | null>(null)
const message = ref('')
const error = ref('')
const loading = ref(true)

const trialBalanced = computed(() => Boolean(opening.value && opening.value.trialDebit === opening.value.trialCredit && opening.value.inventoryLedger === opening.value.inventoryAccount))
const canActivate = computed(() => trialBalanced.value && opening.value?.status !== 'live' && canPermission('journal_entry:submit'))

async function load() {
  loading.value = true
  try {
    opening.value = await fetchOpening()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  }
  finally {
    loading.value = false
  }
}

async function balance() {
  message.value = ''
  error.value = ''
  try {
    opening.value = await balanceOpeningTrial()
    message.value = '期初试算已平衡；启用仍需另一人批准。'
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : '操作失败'
  }
}

async function activate() {
  message.value = ''
  error.value = ''
  try {
    opening.value = await activateOpeningBatch()
    message.value = '期初已启用，业务单据现在可以过账。'
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : '启用失败'
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="d-flex justify-space-between align-center flex-wrap gap-4 mb-6">
      <div>
        <h4 class="text-h4">
          期初导入与启用
        </h4>
        <p class="text-body-1 mb-0">
          科目期初、库存期初、应收应付期初必须一起试算；启用前业务单据只能保存草稿。
        </p>
      </div>
      <div class="d-flex gap-3">
        <VBtn
          variant="tonal"
          :loading="loading"
          @click="load"
        >
          刷新
        </VBtn>
        <VBtn
          data-test="opening-activate"
          :disabled="!canActivate"
          :title="canActivate ? undefined : '试算不平或无启用权限'"
          @click="activate"
        >
          启用期初
        </VBtn>
      </div>
    </div>
    <VAlert
      v-if="message"
      type="success"
      variant="tonal"
      class="mb-4"
    >
      {{ message }}
    </VAlert>
    <VAlert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-4"
    >
      {{ error }}
    </VAlert>
    <VAlert
      type="info"
      variant="tonal"
      class="mb-6"
    >
      中国会计准则 · 人民币本位币 · 演示默认值，真实使用前需核实。当前操作者：{{ session.displayName }}
    </VAlert>
    <VRow v-if="opening">
      <VCol
        cols="12"
        md="8"
      >
        <VCard
          title="期初批次"
          class="mb-6"
        >
          <VCardText>
            <div class="d-flex justify-space-between align-center mb-4">
              <span>批次 {{ opening.id }}</span>
              <StatusChip
                domain="generic"
                :value="opening.status"
              />
            </div>
            <VTable>
              <thead>
                <tr>
                  <th>类别</th><th>条数</th><th class="text-end">
                    金额
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>科目余额</td><td>{{ opening.stockRows.length + opening.invoiceRows.length }}</td><td class="text-end">
                    <MoneyText
                      :amount="opening.trialDebit"
                      currency="CNY"
                      minor
                    />
                  </td>
                </tr>
                <tr>
                  <td>库存台账期初</td><td>{{ opening.stockRows.length }}</td><td class="text-end">
                    <MoneyText
                      :amount="opening.inventoryLedger"
                      currency="CNY"
                      minor
                    />
                  </td>
                </tr>
                <tr>
                  <td>应收应付期初</td><td>{{ opening.invoiceRows.length }}</td><td class="text-end">
                    按单据原币与本位币导入
                  </td>
                </tr>
              </tbody>
            </VTable>
          </VCardText>
        </VCard>
        <VCard
          title="库存期初行"
          class="mb-6"
        >
          <VTable>
            <thead>
              <tr>
                <th>SKU</th><th>仓库</th><th>数量</th><th class="text-end">
                  金额
                </th>
              </tr>
            </thead><tbody>
              <tr
                v-for="line in opening.stockRows"
                :key="`${line.sku}-${line.warehouse}`"
              >
                <td>{{ line.sku }}</td><td>{{ line.warehouse }}</td><td>{{ line.qty }}</td><td class="text-end">
                  <MoneyText
                    :amount="line.amount"
                    currency="CNY"
                    minor
                  />
                </td>
              </tr>
            </tbody>
          </VTable>
        </VCard>
      </VCol>
      <VCol
        cols="12"
        md="4"
      >
        <VCard
          title="试算校验"
          class="mb-6"
        >
          <VCardText>
            <div class="d-flex justify-space-between mb-2">
              <span>借方合计</span><MoneyText
                :amount="opening.trialDebit"
                currency="CNY"
                minor
              />
            </div>
            <div class="d-flex justify-space-between mb-2">
              <span>贷方合计</span><MoneyText
                :amount="opening.trialCredit"
                currency="CNY"
                minor
              />
            </div>
            <VAlert
              :type="trialBalanced ? 'success' : 'error'"
              variant="tonal"
              class="mt-4"
            >
              {{ trialBalanced ? '借贷平衡且库存金额相等' : '借贷不平或库存金额不齐，启用不可用' }}
            </VAlert>
            <VBtn
              v-if="!trialBalanced"
              block
              class="mt-4"
              variant="tonal"
              data-test="opening-balance"
              @click="balance"
            >
              加载平衡演示数据
            </VBtn>
            <div
              v-if="opening.preparedBy"
              class="text-caption text-medium-emphasis mt-4"
            >
              准备人：{{ opening.preparedBy }}；启用必须由另一人批准。
            </div>
          </VCardText>
        </VCard>
        <VCard title="业务状态">
          <VCardText>启用前业务单据不可过账；启用后期初凭证视为已过账，更正只能走红字冲销。</VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>
