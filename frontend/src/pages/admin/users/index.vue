<script setup lang="ts">
import { fetchAdminUsers } from '@/api/admin'
import ModuleTable from '@/components/biz/ModuleTable.vue'

const router = useRouter()

const rows = ref<Array<{ id: string
  [key: string]: unknown }>>([])

onMounted(async () => {
  rows.value = await fetchAdminUsers()
})

const columns = [{ key: 'name', title: '用户' }, { key: 'email', title: '邮箱' }, { key: 'role', title: '角色' }, { key: 'stores', title: '店铺范围' }, { key: 'status', title: '状态' }]
</script>

<template>
  <ModuleTable
    storage-key="admin-users"
    title="用户"
    subtitle="管理登录账号与店铺范围。"
    :rows="rows"
    :columns="columns"
    @open="router.push(`/admin/users/${$event.id}`)"
  >
    <template #cell.role="{ item }">
      <VChip
        size="small"
        color="primary"
        variant="tonal"
      >
        {{ item.role }}
      </VChip>
    </template>
  </ModuleTable>
</template>
