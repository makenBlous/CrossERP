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
