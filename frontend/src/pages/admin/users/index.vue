<script setup lang="ts">
import { fetchAdminUsers } from '@/api/admin'
import ListPage from '@/components/biz/ListPage.vue'

const router = useRouter()

const rows = ref<Array<{ id: string
  [key: string]: unknown }>>([])

onMounted(async () => {
  rows.value = await fetchAdminUsers()
})

const columns = [{ key: 'name', title: '用户' }, { key: 'email', title: '邮箱' }, { key: 'role', title: '角色' }, { key: 'stores', title: '店铺范围' }, { key: 'status', title: '状态' }]
</script>

<template>
  <ListPage
    storage-key="admin-users"
    title="用户"
    subtitle="管理登录账号与店铺范围。"
    :items="rows"
    :columns="columns"
    @open="router.push(`/admin/users/${$event.id}`)"
  >
    <template #item.role="{ item }">
      <VChip
        size="small"
        color="primary"
        variant="tonal"
      >
        {{ item.role }}
      </VChip>
    </template>
  </ListPage>
</template>
