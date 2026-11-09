<script setup lang="ts">
import { fetchColumnMap, fetchColumnMaps, saveColumnMapEntry } from '@/api/finance'
import { useConfirm } from '@/composables/useConfirm'
import EmptyState from '@/components/biz/EmptyState.vue'

const { confirm } = useConfirm()
const templates = ref<Awaited<ReturnType<typeof fetchColumnMaps>>>([])
const selectedId = ref('')
const selected = ref<Awaited<ReturnType<typeof fetchColumnMap>>>(null)
const mappings = ref<Array<{ source: string; field: string }>>([])
const standardFields = ['order_no', 'platform_sku', 'internal_sku', 'amount', 'currency', 'unit_cost', 'valid_from', 'payout_id']

onMounted(async () => {
  templates.value = await fetchColumnMaps()
  selectedId.value = templates.value[0]?.id ?? ''
  await loadSelected()
})

async function loadSelected() {
  if (!selectedId.value)
    return
  selected.value = await fetchColumnMap(selectedId.value)
  mappings.value = selected.value?.mappings?.map(item => ({ ...item })) ?? []
}

async function save() {
  const ok = await confirm({ title: '保存列映射', text: '保存后将记录审计日志，确认继续吗？', confirmText: '确认保存', cancelText: '取消' })
  if (!ok)
    return
  await saveColumnMapEntry(selectedId.value, mappings.value)
  await loadSelected()
}
</script>

<template>
  <div>
    <div class="mb-6"><h4 class="text-h4">列映射模板</h4><p class="text-body-1 text-medium-emphasis mb-0">选择模板后逐列确认来源字段与标准字段。</p></div>
    <VRow>
      <VCol cols="12" md="4">
        <VCard title="模板列表">
          <VList v-if="templates.length">
            <VListItem v-for="item in templates" :key="item.id" :active="item.id === selectedId" @click="selectedId = item.id; loadSelected()">
              <VListItemTitle>{{ item.name }}</VListItemTitle>
              <VListItemSubtitle>{{ item.connector }} · {{ item.status }}</VListItemSubtitle>
            </VListItem>
          </VList>
          <EmptyState v-else />
        </VCard>
      </VCol>
      <VCol cols="12" md="8">
        <VCard v-if="selected" :title="selected.name">
          <VCardText>
            <VTable density="compact">
              <thead><tr><th>来源列</th><th>标准字段</th></tr></thead>
              <tbody>
                <tr v-for="(mapping, index) in mappings" :key="`${mapping.source}-${index}`">
                  <td>{{ mapping.source }}</td>
                  <td><AppSelect v-model="mapping.field" :items="standardFields" hide-details /></td>
                </tr>
              </tbody>
            </VTable>
            <div class="d-flex justify-end mt-4"><VBtn @click="save">保存映射</VBtn></div>
          </VCardText>
        </VCard>
        <EmptyState v-else title="未选择模板" />
      </VCol>
    </VRow>
  </div>
</template>
