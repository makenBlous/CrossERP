<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { fetchContact } from '@/api/crm'; import DetailPage from '@/components/biz/DetailPage.vue'

const route = useRoute(); const router = useRouter(); const item = ref<any>(null)

onMounted(async () => { item.value = await fetchContact(String((route.params as Record<string, unknown>).id)) })
</script>

<template>
  <DetailPage
    v-if="item"
    :title="item.name"
    :subtitle="`${item.title} · ${item.accountName}`"
    :related="[{ id: item.accountId, type: '客户', label: item.accountName, to: `/crm/accounts/${item.accountId}` }]"
  >
    <VCard title="联系方式">
      <VCardText>
        <VList>
          <VListItem
            prepend-icon="tabler-mail"
            title="邮箱"
            :subtitle="item.email"
          /><VListItem
            prepend-icon="tabler-building"
            title="所属客户"
            :subtitle="item.accountName"
          />
        </VList>
      </VCardText>
    </VCard><VBtn
      class="mt-4"
      variant="tonal"
      @click="router.push('/crm/contacts')"
    >
      返回联系人
    </VBtn>
  </DetailPage>
</template>
