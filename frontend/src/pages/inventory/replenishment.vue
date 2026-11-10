<script setup lang="ts">
import { getLatestReplenishmentPlan, runPlan } from '@/api/replenishment'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import GapBPage from '@/views/gap-b/GapBPage.vue'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const message = ref('')
const running = ref(false)

async function openVersion() {
  try {
    const plan = await getLatestReplenishmentPlan()
    if (!plan)
      throw new Error(t('replenishment.missing'))
    await router.push({ path: `/inventory/replenishment/plans/${plan.id}` })
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
}

async function runNew() {
  running.value = true
  try {
    const plan = await runPlan()

    message.value = t('replenishment.runSuccess')
    await router.push({ path: `/inventory/replenishment/plans/${plan.id}` })
  }
  catch (err) {
    message.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    running.value = false
  }
}
</script>

<template>
  <div>
    <VAlert
      v-if="message"
      type="info"
      variant="tonal"
      closable
      class="mb-4"
      @click:close="message = ''"
    >
      {{ message }}
    </VAlert>
    <div class="d-flex justify-end flex-wrap ga-2 mb-4">
      <VBtn
        variant="tonal"
        data-test="open-latest-replenishment-version"
        @click="openVersion"
      >
        {{ t('replenishment.openVersion') }}
      </VBtn>
      <PermissionGate permission="material_request:create">
        <VBtn
          color="primary"
          data-test="run-replenishment-plan"
          :loading="running"
          @click="runNew"
        >
          {{ t('replenishment.run') }}
        </VBtn>
      </PermissionGate>
    </div>
    <GapBPage page-key="I13" />
  </div>
</template>
