<script setup lang="ts">
import type { CurrencyCode } from '@/types/domain'
import { formatMoney } from '@/utils/format'
import { toDisplay } from '@/utils/money'

const props = defineProps<{
  amount: number
  currency: CurrencyCode
  converted?: number | null
  convertedCurrency?: CurrencyCode
  minor?: boolean
}>()

const { t } = useI18n({ useScope: 'global' })
const displayAmount = computed(() => props.minor ? toDisplay(props.amount, props.currency) : props.amount)
const convertedAmount = computed(() => props.converted == null || !props.convertedCurrency ? null : props.minor ? toDisplay(props.converted, props.convertedCurrency) : props.converted)
</script>

<template>
  <!-- Vuexy 没有金额展示组件，也不知道币种和折算额。这里只格式化，不计算。 -->
  <span>
    {{ formatMoney(displayAmount, currency) }}
    <span
      v-if="convertedAmount != null && convertedCurrency"
      class="text-caption text-medium-emphasis ms-1"
    >
      {{ t('foundation.converted') }} {{ formatMoney(convertedAmount, convertedCurrency) }}
    </span>
  </span>
</template>
