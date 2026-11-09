/* eslint-disable max-statements-per-line */
<script setup lang="ts">
/* eslint-disable max-statements-per-line */
const steps = [{ title: '提交', text: '运营创建凭证草稿或核销申请。' }, { title: '财务审核', text: '财务检查快照、借贷平衡和附件。' }, { title: '管理员复核', text: '管理员可在需要时复核审批。' }, { title: '后端过账', text: '批准后由 ledger 服务执行写账与导出。' }]
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        流程配置
      </h4><p class="text-body-1 text-medium-emphasis mb-0">
        审批步骤采用 Vuexy form-wizard-icons 的分步结构。
      </p>
    </div><VCard>
      <VCardText>
        <VExpansionPanels>
          <VExpansionPanel
            v-for="step in steps"
            :key="step.title"
            :title="step.title"
          >
            <VExpansionPanelText>{{ step.text }}</VExpansionPanelText>
          </VExpansionPanel>
        </VExpansionPanels>
      </VCardText>
    </VCard>
  </div>
</template>

