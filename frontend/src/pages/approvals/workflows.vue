<script setup lang="ts">
import { auditApprovalWorkflowEdit } from '@/api/approvals'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import { type ApprovalWorkflowStep, approvalWorkflowTemplates } from '@/mocks/services/approvals'
import { useSessionStore } from '@/stores/session'

const { t } = useI18n({ useScope: 'global' })
const session = useSessionStore()
const admin = computed(() => session.role === 'admin')
const documentTypes = ['voucher', 'purchase_order', 'clearing', 'allocation', 'agent_suggestion'] as const
const labels: Record<typeof documentTypes[number], string> = { voucher: '凭证', purchase_order: '采购单', clearing: '收付款核销', allocation: '广告分摊', agent_suggestion: '智能体建议' }
const workflows = reactive<Record<string, ApprovalWorkflowStep[]>>(Object.fromEntries(documentTypes.map(type => [type, approvalWorkflowTemplates[type].map(step => ({ ...step }))])))
const editOpen = ref(false)
const editType = ref('voucher')
const editIndex = ref(0)
const editRole = ref('')
const editOrder = ref(1)
const roles = ['运营', '采购', '财务', '管理员', '智能体']

function edit(type: string, index: number) {
  if (!admin.value)
    return
  const step = workflows[type][index]

  editType.value = type
  editIndex.value = index
  editRole.value = step.role
  editOrder.value = index + 1
  editOpen.value = true
}

async function saveEdit() {
  const steps = workflows[editType.value]
  const step = { ...steps[editIndex.value], role: editRole.value }
  const target = Math.min(Math.max(editOrder.value - 1, 0), steps.length - 1)

  steps.splice(editIndex.value, 1)
  steps.splice(target, 0, step)
  await auditApprovalWorkflowEdit(editType.value, step)
  editOpen.value = false
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        {{ t('approvals.workflows') }}
      </h4>
      <p class="text-body-1 text-medium-emphasis mb-0">
        {{ t('approvals.workflowSubtitle') }}
      </p>
    </div>
    <VAlert
      type="info"
      variant="tonal"
      class="mb-6"
    >
      {{ t('approvals.later') }}
    </VAlert>
    <VRow>
      <VCol
        v-for="type in documentTypes"
        :key="type"
        cols="12"
        lg="6"
      >
        <VCard :title="labels[type]">
          <VCardText>
            <VRow>
              <VCol
                cols="12"
                md="4"
              >
                <AppStepper
                  :items="workflows[type].map(step => ({ title: step.title, subtitle: step.role, icon: 'tabler-check' }))"
                  direction="vertical"
                  icon-size="22"
                  class="stepper-icon-step-bg"
                />
              </VCol>
              <VCol
                cols="12"
                md="8"
              >
                <VList density="compact">
                  <VListItem
                    v-for="(step, index) in workflows[type]"
                    :key="step.id"
                  >
                    <VListItemTitle>{{ index + 1 }}. {{ step.title }}</VListItemTitle>
                    <VListItemSubtitle>{{ t('approvals.approverRole') }}：{{ step.role }} · {{ t('approvals.ownRule') }}</VListItemSubtitle>
                    <template #append>
                      <VBtn
                        v-if="admin"
                        size="small"
                        variant="text"
                        @click="edit(type, index)"
                      >
                        {{ t('common.edit') }}
                      </VBtn>
                    </template>
                  </VListItem>
                </VList>
              </VCol>
            </VRow>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
    <FormDrawer
      v-model="editOpen"
      :title="t('approvals.editWorkflow')"
      @save="saveEdit"
    >
      <AppSelect
        v-model="editRole"
        :items="roles"
        :label="t('approvals.approverRole')"
      />
      <AppTextField
        v-model.number="editOrder"
        type="number"
        min="1"
        :label="t('approvals.stepOrder')"
        class="mt-4"
      />
    </FormDrawer>
  </div>
</template>
