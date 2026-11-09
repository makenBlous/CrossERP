<script setup lang="ts">
import type { CurrencyCode } from '@/types/domain'
import { formatMoney } from '@/utils/format'

defineProps<{
  amount: number
  currency: CurrencyCode
  converted?: number | null
  convertedCurrency?: CurrencyCode
}>()

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <!-- Vuexy 没有金额展示组件，也不知道币种和折算额。这里只格式化，不计算。 -->
  <span>
    {{ formatMoney(amount, currency) }}
    <span
      v-if="converted != null && convertedCurrency"
      class="text-caption text-medium-emphasis ms-1"
    >
      {{ t('foundation.converted') }} {{ formatMoney(converted, convertedCurrency) }}
    </span>
  </span>
</template>
