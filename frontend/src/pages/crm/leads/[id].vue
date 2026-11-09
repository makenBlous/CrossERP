<script setup lang="ts">
import { convertCrmLead, fetchLead } from '@/api/crm'
import DetailPage from '@/components/biz/DetailPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'

const route = useRoute()
const router = useRouter()
const lead = ref<any>(null)
const dialog = ref(false)

onMounted(async () => {
  lead.value = await fetchLead(String((route.params as Record<string, unknown>).id))
})

const relatedLinks = computed(() => {
  const item = lead.value
  if (!item)
    return []

  return [
    item.accountId ? { id: item.accountId, type: '客户', label: item.accountId, to: `/crm/accounts/${item.accountId}` } : null,
    item.contactId ? { id: item.contactId, type: '联系人', label: item.contactId, to: `/crm/contacts/${item.contactId}` } : null,
    item.opportunityId ? { id: item.opportunityId, type: '商机', label: item.opportunityId, to: `/crm/opportunities/${item.opportunityId}` } : null,
  ].filter(Boolean) as { id: string; type: string; label: string; to: string }[]
})

async function convert() {
  const result = await convertCrmLead(String((route.params as Record<string, unknown>).id))
  if (result) {
    lead.value = result.lead
    dialog.value = false
  }
}
</script>

<template>
  <DetailPage
    v-if="lead"
    :title="lead.name"
    :subtitle="`${lead.company} · ${lead.email}`"
    domain="crm"
    :status="lead.stage"
    :related="relatedLinks"
  >
    <template #actions>
      <PermissionGate action="create">
        <VBtn
          color="primary"
          @click="dialog = true"
        >
          转化为客户
        </VBtn>
      </PermissionGate><VBtn
        variant="tonal"
        @click="router.push('/crm/leads/board')"
      >
        返回看板
      </VBtn>
    </template><VCard title="线索资料">
      <VCardText>
        <VRow>
          <VCol
            cols="12"
            md="6"
          >
            <div class="text-caption">
              来源
            </div><div>{{ lead.source }}</div>
          </VCol><VCol
            cols="12"
            md="6"
          >
            <div class="text-caption">
              负责人
            </div><div>{{ lead.owner }}</div>
          </VCol>
        </VRow><VAlert
          class="mt-4"
          type="info"
          variant="tonal"
        >
          转化会创建客户、联系人和商机，并保留关联 ID。
        </VAlert>
      </VCardText>
    </VCard>
  </DetailPage><VDialog
    v-model="dialog"
    max-width="420"
  >
    <VCard title="确认线索转化">
      <VCardText>将为「{{ lead?.company }}」创建客户、联系人和商机。</VCardText><VCardActions>
        <VSpacer /><VBtn
          variant="text"
          @click="dialog = false"
        >
          取消
        </VBtn><VBtn
          color="primary"
          @click="convert"
        >
          确认转化
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>
