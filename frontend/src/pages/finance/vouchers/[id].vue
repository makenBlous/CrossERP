<script setup lang="ts">
import { decideGapAVoucher, fetchGapAVoucher, submitGapAVoucher } from '@/api/gap-a'
import DetailPage from '@/components/biz/DetailPage.vue'
import EmptyState from '@/components/biz/EmptyState.vue'
import MoneyText from '@/components/biz/MoneyText.vue'
import { useSessionStore } from '@/stores/session'
import type { GapAVoucher } from '@/types/gap-a'

const route = useRoute()
const session = useSessionStore()
const row = ref<GapAVoucher | null>(null)
const message = ref('')
const submitting = ref(false)
const canSubmit = computed(() => Boolean(row.value && row.value.status === 'draft' && ['admin', 'operator', 'finance', 'accountant', 'finance_manager'].includes(session.role)))
const canApprove = computed(() => Boolean(row.value && row.value.status === 'pending' && ['admin', 'finance', 'accountant', 'finance_manager'].includes(session.role) && session.displayName !== '演示运营'))

async function load() { row.value = await fetchGapAVoucher(String((route.params as Record<string, string | undefined>).id ?? '')) as GapAVoucher | null }
onMounted(load)
async function submit() { if (!row.value || !canSubmit.value) return; submitting.value = true; try { await submitGapAVoucher(row.value.id); message.value = '已提交审批，批准前不会写入总账。'; await load() } catch (error) { message.value = error instanceof Error ? error.message : '提交失败' } finally { submitting.value = false } }
async function decide(approved: boolean) { if (!row.value || !canApprove.value) return; try { await decideGapAVoucher(row.value.id, approved); message.value = approved ? '凭证已批准，可进入总账。' : '凭证已驳回。'; await load() } catch (error) { message.value = error instanceof Error ? error.message : '审批失败' } }
</script>

<template>
  <DetailPage v-if="row" :title="row.no" :subtitle="`${row.period} · ${row.summary}`" domain="voucher" :status="row.status" :timeline="row.timeline.map(event => ({ id: event.id, at: event.at, title: event.action, detail: event.detail, actor: event.actor }))" :related="row.sourceLinks.map(link => ({ id: link.sourceId, type: link.sourceType, label: link.label, to: link.to }))">
    <template #actions>
      <VBtn v-if="canSubmit" prepend-icon="tabler-send" :loading="submitting" @click="submit">提交审批</VBtn>
      <VBtn v-if="canApprove" color="success" @click="decide(true)">批准</VBtn>
      <VBtn v-if="canApprove" color="error" variant="tonal" @click="decide(false)">驳回</VBtn>
      <VBtn v-if="row.status === 'approved'" variant="tonal" prepend-icon="tabler-download" @click="message = '已生成通用 Excel 凭证文件（演示）。'">下载已批准文件</VBtn>
    </template>
    <VAlert v-if="message" type="success" variant="tonal" class="mb-6">{{ message }}</VAlert>
    <VCard title="凭证分录" class="mb-6"><VTable><thead><tr><th>科目</th><th>摘要</th><th class="text-end">借方</th><th class="text-end">贷方</th></tr></thead><tbody><tr><td>主营业务成本</td><td>{{ row.summary }}</td><td class="text-end"><MoneyText :amount="row.debit" minor currency="CNY" /></td><td class="text-end">—</td></tr><tr><td>平台结算清算</td><td>{{ row.summary }}</td><td class="text-end">—</td><td class="text-end"><MoneyText :amount="row.credit" minor currency="CNY" /></td></tr></tbody></VTable><VCardText class="d-flex align-center gap-3 flex-wrap"><VChip color="success" size="small">借贷平衡</VChip><span>借方合计：<MoneyText :amount="row.debit" minor currency="CNY" /></span><span>贷方合计：<MoneyText :amount="row.credit" minor currency="CNY" /></span></VCardText></VCard>
    <VCard title="来源追溯"><VList><VListItem v-for="link in row.sourceLinks" :key="link.sourceId" :to="link.to"><VListItemTitle>{{ link.label }}</VListItemTitle><VListItemSubtitle>{{ link.sourceType }} · <MoneyText :amount="link.amount" minor :currency="link.currency" /></VListItemSubtitle></VListItem></VList></VCard>
  </DetailPage>
  <EmptyState v-else title="未找到凭证" text="该凭证 ID 不存在。" back-to="/finance/vouchers" />
</template>
