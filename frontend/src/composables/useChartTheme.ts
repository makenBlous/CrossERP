import { computed } from 'vue'
import { useTheme } from 'vuetify'

export function useChartTheme() {
  const theme = useTheme()
  const label = computed(() => theme.current.value.dark ? 'rgba(225, 222, 245, 0.78)' : 'rgba(47, 43, 61, 0.78)')
  const grid = computed(() => theme.current.value.dark ? 'rgba(225, 222, 245, 0.12)' : 'rgba(47, 43, 61, 0.12)')
  const primary = computed(() => theme.current.value.colors.primary)
  const success = computed(() => theme.current.value.colors.success)
  const warning = computed(() => theme.current.value.colors.warning)
  const info = computed(() => theme.current.value.colors.info)
  const error = computed(() => theme.current.value.colors.error)

  return { label, grid, primary, success, warning, info, error }
}
