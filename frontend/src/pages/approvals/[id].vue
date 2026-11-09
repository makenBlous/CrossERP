<script setup lang="ts">
import { decideApproval, fetchApproval } from '@/api/approvals'
import DetailPage from '@/components/biz/DetailPage.vue'
import EmptyState from '@/components/biz/EmptyState.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const row = ref<NonNullable<Awaited<ReturnType<typeof fetchApproval>>> | null>(null)
const comment = ref('')
const saving = ref(false)

const canDecide = computed(() => Boolean(row.value && row.value.status === 'pending' && ['admin', 'finance'].includes(session.role) && row.value.submitter !== session.displayName))

onMounted(async () => {
  row.value = await fetchApproval(String(route.params.id))
  comment.value = row.value?.comment ?? ''
})

async function decide(status: 'approved' | 'rejected') {
  if (!row.value || !canDecide.value)
    return
  saving.value = true
  row.value = await decideApproval(row.value.id, status, comment.value)
  saving.value = false
}
</script>

<template>
  <DetailPage
    v-if="row"
    :title="row.title"
    :subtitle="`${row.type} · ${row.submitter} · ${row.submittedAt}`"
    domain="approval"
    :status="row.status"
    :timeline="row.timeline"
  >
    <template #actions>
      <VBtn
        variant="tonal"
        @click="router.push('/approvals')"
      >
        返回审批台
      </VBtn>
    </template>
    <VCard
      title="只读快照"
      class="mb-6"
    >
      <VCardText>
        <p>{{ row.summary }}</p>
        <div class="text-caption font-monospace">
          内容哈希：{{ row.payloadHash || `sha256:${row.id}` }}
        </div>
        <VTable class="mt-4">
          <thead>
            <tr>
              <th>科目</th>
              <th class="text-end">借方</th>
              <th class="text-end">贷方</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="line in row.lines"
              :key="line.account"
            >
              <td>{{ line.account }}</td>
              <td class="text-end">
                <MoneyText
                  v-if="line.debit"
                  :amount="line.debit"
                  :currency="row.currency"
                />
                <span v-else>—</span>
              </td>
              <td class="text-end">
                <MoneyText
                  v-if="line.credit"
                  :amount="line.credit"
                  :currency="row.currency"
                />
                <span v-else>—</span>
              </td>
            </tr>
          </tbody>
        </VTable>
      </VCardText>
    </VCard>
    <VCard title="审批意见">
      <VCardText>
        <AppTextarea
          v-model="comment"
          label="意见"
          rows="3"
          :readonly="!canDecide"
        />
        <VAlert
          v-if="!canDecide && row.status === 'pending'"
          type="warning"
          variant="tonal"
          class="mt-4"
        >
          当前角色不能审批自己的提交，或没有审批权限。
        </VAlert>
        <div class="d-flex gap-3 mt-4">
          <VBtn
            color="success"
            :disabled="!canDecide"
            :loading="saving"
            @click="decide('approved')"
          >
            批准
          </VBtn>
          <VBtn
            color="error"
            variant="tonal"
            :disabled="!canDecide"
            :loading="saving"
            @click="decide('rejected')"
          >
            驳回
          </VBtn>
        </div>
      </VCardText>
    </VCard>
  </DetailPage>
  <div v-else>
    <EmptyState title="未找到审批" text="该审批 ID 不存在。" />
    <VBtn
      class="mt-4"
      variant="tonal"
      @click="router.push('/approvals')"
    >
      返回审批台
    </VBtn>
  </div>
</template>
