<script setup lang="ts">
import type { CalendarOptions, EventClickArg } from '@fullcalendar/core'
import zhCn from '@fullcalendar/core/locales/zh-cn'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import listPlugin from '@fullcalendar/list'
import timeGridPlugin from '@fullcalendar/timegrid'
import FullCalendar from '@fullcalendar/vue3'
import { fetchCalendar } from '@/api/dashboard'
import { usePageContext } from '@/composables/usePageContext'
import type { CalendarEventRow } from '@/types/domain'

const { t, locale } = useI18n({ useScope: 'global' })
const router = useRouter()
const { setSelected } = usePageContext()
const events = ref<CalendarEventRow[]>([])
const selected = ref<CalendarEventRow | null>(null)
const loading = ref(true)
const error = ref('')

const kindColor: Record<string, string> = {
  arrival: '#28c76f',
  payout: '#00cfe8',
  ship: '#7367f0',
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    events.value = await fetchCalendar()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : t('foundation.errorTitle')
  }
  finally {
    loading.value = false
  }
}

onMounted(load)
onUnmounted(() => setSelected(null))

function pick(info: EventClickArg) {
  const found = events.value.find(item => item.id === info.event.id) ?? null

  selected.value = found
  setSelected(found?.id ?? null)
}

const options = computed<CalendarOptions>(() => ({
  plugins: [dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin],
  initialView: 'dayGridMonth',
  initialDate: '2026-10-01',
  height: 720,
  locale: String(locale.value).startsWith('en') ? 'en' : zhCn,
  headerToolbar: {
    start: 'prev,next today',
    center: 'title',
    end: 'dayGridMonth,timeGridWeek,listMonth',
  },
  events: events.value.map(item => ({
    id: item.id,
    title: item.title,
    start: item.start,
    color: kindColor[item.kind] ?? '#7367f0',
  })),
  eventClick: pick,
}))

function openSelected() {
  if (selected.value)
    router.push({ path: selected.value.to })
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        {{ t('calendar.title') }}
      </h4>
      <p class="text-body-1 text-medium-emphasis mb-0">
        {{ t('calendar.subtitle') }}
      </p>
    </div>
    <ErrorState
      v-if="error"
      :text="error"
      class="mb-4"
      @retry="load"
    />
    <LoadingState v-if="loading" />
    <VRow v-else>
      <VCol
        cols="12"
        lg="9"
      >
        <VCard>
          <VCardText>
            <FullCalendar :options="options" />
          </VCardText>
        </VCard>
      </VCol>
      <VCol
        cols="12"
        lg="3"
      >
        <VCard>
          <VCardItem>
            <VCardTitle>{{ t('calendar.selected') }}</VCardTitle>
          </VCardItem>
          <VCardText v-if="selected">
            <div class="text-subtitle-1 mb-2">
              {{ selected.title }}
            </div>
            <div class="text-medium-emphasis mb-4">
              {{ selected.start }}
            </div>
            <VBtn
              color="primary"
              :to="{ path: selected.to }"
              @click="openSelected"
            >
              {{ t('todos.jump') }}
            </VBtn>
          </VCardText>
          <VCardText v-else>
            <EmptyState />
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>

<style lang="scss">
@use "@core/scss/template/libs/full-calendar";
</style>
