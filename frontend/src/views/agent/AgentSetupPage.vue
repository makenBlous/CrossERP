<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <div>
    <div class="d-flex align-center justify-space-between mb-6">
      <div>
        <h4 class="text-h4">
          {{ t('agentModule.deerflow.title') }}
        </h4><p class="text-body-1 text-medium-emphasis mb-0">
          {{ t('agentModule.subtitle') }}
        </p>
      </div><VChip
        color="info"
        variant="tonal"
      >
        <VIcon
          start
          icon="tabler-shield-lock"
        />{{ t('agentModule.readOnly') }}
      </VChip>
    </div><VAlert
      type="warning"
      variant="tonal"
      class="mb-6"
    >
      {{ t('agentModule.writeBoundary') }}
    </VAlert><VRow>
      <VCol
        cols="12"
        md="5"
      >
        <VCard>
          <VCardItem><VCardTitle>{{ t('agentModule.deerflow.connection') }}</VCardTitle></VCardItem><VCardText>
            <VChip
              color="success"
              class="mb-4"
            >
              {{ t('agentModule.deerflow.mockConnected') }}
            </VChip><AppTextField
              model-value="http://127.0.0.1:2026"
              label="Base URL"
              readonly
            /><AppTextField
              model-value="v2.x"
              label="Version"
              readonly
            /><VSwitch
              :model-value="false"
              label="Enabled for local preview"
            />
          </VCardText>
        </VCard>
      </VCol><VCol
        cols="12"
        md="7"
      >
        <VCard>
          <VCardItem><VCardTitle>{{ t('agentModule.deerflow.setup') }}</VCardTitle></VCardItem><VCardText>
            <VStepper
              :items="[t('agentModule.deerflow.step1'), t('agentModule.deerflow.step2'), t('agentModule.deerflow.step3')]"
              hide-actions
            >
              <template #item.1>
                <VAlert
                  type="info"
                  variant="tonal"
                >
                  {{ t('agentModule.deerflow.step1Hint') }}
                </VAlert>
              </template><template #item.2>
                <VList>
                  <VListItem
                    title="/mcp/tools"
                    subtitle="CrossERP 只读工具清单"
                  /><VListItem
                    title="/mcp/ask"
                    subtitle="生成待审批建议的入口"
                  />
                </VList>
              </template><template #item.3>
                <VAlert
                  type="warning"
                  variant="tonal"
                >
                  {{ t('agentModule.deerflow.keyHint') }}
                </VAlert>
              </template>
            </VStepper>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>
