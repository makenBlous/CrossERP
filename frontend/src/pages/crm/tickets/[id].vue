<script setup lang="ts">
import { fetchTicket, updateCrmTicketStatus } from '@/api/crm'
import DetailPage from '@/components/biz/DetailPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'

const route = useRoute()
const router = useRouter()
const item = ref<any>(null)

onMounted(async () => {
  item.value = await fetchTicket(String((route.params as Record<string, unknown>).id))
})

async function setStatus(status: string) {
  await updateCrmTicketStatus(String((route.params as Record<string, unknown>).id), status)
  item.value.status = status
  item.value = await fetchTicket(String((route.params as Record<string, unknown>).id))
}
</script>

<template>
  <DetailPage
    v-if="item"
    :title="item.subject"
    :subtitle="`${item.account?.name ?? item.accountId} · 工单 ${item.id}`"
    domain="generic"
    :status="item.status"
    :related="item.orderId ? [{ id: item.orderId, type: '订单', label: item.orderNo, to: `/orders/${item.orderId}` }] : []"
  >
    <template #actions>
      <PermissionGate action="update">
        <VBtn
          v-if="item.status !== '处理中'"
          color="primary"
          @click="setStatus('处理中')"
        >
          处理中
        </VBtn><VBtn
          v-if="item.status !== '已解决'"
          color="success"
          variant="tonal"
          @click="setStatus('已解决')"
        >
          已解决
        </VBtn>
      </PermissionGate>
    </template><VCard title="会话">
      <VCardText>
        <div
          v-for="message in item.messages"
          :key="message.id || message.at"
          class="d-flex gap-3 mb-4"
        >
          <VAvatar
            color="primary"
            variant="tonal"
            size="36"
          >
            <VIcon icon="tabler-message" />
          </VAvatar><div>
            <div class="font-weight-medium">
              {{ message.author }} <span class="text-caption text-disabled ms-2">{{ message.at }}</span>
            </div><div class="text-body-2 mt-1">
              {{ message.text }}
            </div>
          </div>
        </div><VAlert
          v-if="item.orderNo"
          type="info"
          variant="tonal"
        >
          关联订单：<a
            href="#"
            @click.prevent="router.push(`/orders/${item.orderId}`)"
          >{{ item.orderNo }}</a>
        </VAlert>
      </VCardText>
    </VCard>
  </DetailPage>
</template>
