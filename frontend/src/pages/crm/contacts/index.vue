<script setup lang="ts">
import { fetchCrmContacts } from '@/api/crm'
import ModuleTable from '@/components/biz/ModuleTable.vue'

const router = useRouter()

const rows = ref<Array<{ id: string
  [key: string]: unknown }>>([])

onMounted(async () => {
  rows.value = await fetchCrmContacts()
})

const columns = [{ key: 'name', title: '联系人' }, { key: 'title', title: '职位' }, { key: 'accountName', title: '所属客户' }, { key: 'email', title: '邮箱' }]
</script>

<template>
  <ModuleTable
    storage-key="crm-contacts"
    title="联系人"
    subtitle="管理具体联系人和所属客户。"
    :rows="rows"
    :columns="columns"
    @open="router.push(`/crm/contacts/${$event.id}`)"
  />
</template>
