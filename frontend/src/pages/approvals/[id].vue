/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { decideApproval, fetchApproval } from '@/api/approvals'
import DetailPage from '@/components/biz/DetailPage.vue'
import { useSessionStore } from '@/stores/session'

const route = useRoute(); const session = useSessionStore(); const row = ref<NonNullable<Awaited<ReturnType<typeof fetchApproval>>> | null>(null); const comment = ref(''); const saving = ref(false)
const canDecide = computed(() => (session.role === 'admin' || session.role === 'finance') && row.value?.status === 'pending' && row.value.submitter !== session.displayName)

onMounted(async () => { row.value = await fetchApproval(String((route.params as Record<string, string>).id)) })
async function decide(status: 'approved' | 'rejected') {
  if (!row.value || !canDecide.value)
    return; saving.value = true; row.value = await decideApproval(row.value.id, status); saving.value = false
}
</script>

<template>
  <DetailPage
    v-if="row"
    :title="row.title"
    :subtitle="`${row.type} · ${row.submitter} · ${row.submittedAt}`"
    domain="approval"
    :status="row.status"
  >
    <VCard
      title="只读快照"
      class="mb-6"
    >
      <VCardText>
        <p>{{ row.summary }}</p><div class="text-caption">
          内容哈希：sha256: demo-{{ row.id }}
        </div><VTable class="mt-4">
          <thead>
            <tr>
              <th>科目</th><th class="text-end">
                借方
              </th><th class="text-end">
                贷方
              </th>
            </tr>
          </thead><tbody>
            <tr
              v-for="line in row.lines"
              :key="line.account"
            >
              <td>{{ line.account }}</td><td class="text-end">
                {{ line.debit || '—' }}
              </td><td class="text-end">
                {{ line.credit || '—' }}
              </td>
            </tr>
          </tbody>
        </VTable>
      </VCardText>
    </VCard><VCard title="审批意见">
      <VCardText>
        <AppTextarea
          v-model="comment"
          label="意见（演示）"
          rows="3"
        /><VAlert
          v-if="!canDecide && row.status === 'pending'"
          type="warning"
          variant="tonal"
          class="mt-4"
        >
          当前角色不能审批自己的提交，或没有审批权限。
        </VAlert><div class="d-flex gap-3 mt-4">
          <VBtn
            color="success"
            :disabled="!canDecide"
            :loading="saving"
            @click="decide('approved')"
          >
            通过
          </VBtn><VBtn
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
  </DetailPage><EmptyState v-else />
</template>

