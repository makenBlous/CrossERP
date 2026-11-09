<script setup lang="ts">
import type { CalendarApi, CalendarOptions, EventClickArg } from '@fullcalendar/core'
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
const { isLeftSidebarOpen } = useResponsiveLeftSidebar()
const events = ref<CalendarEventRow[]>([])
const selected = ref<CalendarEventRow | null>(null)
const loading = ref(true)
const error = ref('')
const calendarRef = ref<{ getApi: () => CalendarApi } | null>(null)
const selectedKinds = ref<string[]>(['arrival', 'payout', 'ship'])

const kindColor: Record<string, string> = {
  arrival: 'success',
  payout: 'info',
  ship: 'primary',
}

const kindHex: Record<string, string> = {
  arrival: '#28c76f',
  payout: '#00cfe8',
  ship: '#7367f0',
}

const kindOptions = computed(() => [
  { value: 'arrival', label: t('calendar.arrival'), color: kindColor.arrival },
  { value: 'payout', label: t('calendar.payout'), color: kindColor.payout },
  { value: 'ship', label: t('calendar.ship'), color: kindColor.ship },
])

const checkAll = computed({
  get: () => selectedKinds.value.length === kindOptions.value.length,
  set: (value: boolean) => {
    selectedKinds.value = value ? kindOptions.value.map(item => item.value) : []
  },
})

const visibleEvents = computed(() => events.value.filter(item => selectedKinds.value.includes(item.kind)))

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

function jumpToDate(date: string) {
  if (date)
    calendarRef.value?.getApi().gotoDate(date)
}

const options = computed<CalendarOptions>(() => ({
  plugins: [dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin],
  initialView: 'dayGridMonth',
  initialDate: '2026-10-01',
  height: 'auto',
  locale: String(locale.value).startsWith('en') ? 'en' : zhCn,
  headerToolbar: {
    start: 'prev,next today',
    center: 'title',
    end: 'dayGridMonth,timeGridWeek,listMonth',
  },
  events: visibleEvents.value.map(item => ({
    id: item.id,
    title: item.title,
    start: item.start,
    color: kindHex[item.kind] ?? '#7367f0',
  })),
  eventClick: pick,
}))
</script>

<template>
  <!-- 布局改编自 Vuexy pages/apps/calendar.vue：左栏日期与类型筛选，右侧 FullCalendar。不提供新建事件。 -->
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        {{ t('calendar.title') }}
      </h4>
      <p class="text-body-1 mb-0">
        {{ t('calendar.subtitle') }}
      </p>
    </div>
    <ErrorState
      v-if="error"
      :text="error"
      class="mb-4"
      @retry="load"
    />
    <VSkeletonLoader
      v-if="loading"
      type="image, article"
    />
    <VCard v-else>
      <VLayout style="z-index: 0;">
        <VNavigationDrawer
          v-model="isLeftSidebarOpen"
          data-allow-mismatch
          width="292"
          absolute
          touchless
          location="start"
          class="calendar-add-event-drawer"
          :temporary="$vuetify.display.mdAndDown"
        >
          <div class="d-flex align-center justify-center pa-2">
            <AppDateTimePicker
              id="calendar-date-picker"
              :model-value="selected?.start?.slice(0, 10) || '2026-10-01'"
              :config="{ inline: true }"
              class="calendar-date-picker"
              @update:model-value="jumpToDate"
            />
          </div>
          <VDivider />
          <div class="pa-6">
            <h6 class="text-lg font-weight-medium mb-4">
              {{ t('calendar.filters') }}
            </h6>
            <div class="d-flex flex-column calendars-checkbox">
              <VCheckbox
                v-model="checkAll"
                :label="t('calendar.allKinds')"
              />
              <VCheckbox
                v-for="kind in kindOptions"
                :key="kind.value"
                v-model="selectedKinds"
                :value="kind.value"
                :color="kind.color"
                :label="kind.label"
              />
            </div>
          </div>
          <VDivider />
          <VCardText>
            <div class="text-subtitle-1 mb-2">
              {{ t('calendar.selected') }}
            </div>
            <template v-if="selected">
              <div class="text-body-1 mb-1">
                {{ selected.title }}
              </div>
              <div class="text-medium-emphasis mb-4">
                {{ selected.start }}
              </div>
              <VBtn
                color="primary"
                :to="{ path: selected.to }"
                @click="router.push({ path: selected.to })"
              >
                {{ t('todos.jump') }}
              </VBtn>
            </template>
            <EmptyState v-else />
          </VCardText>
        </VNavigationDrawer>
        <VMain>
          <VCard flat>
            <div
              v-if="$vuetify.display.mdAndDown"
              class="pa-4"
            >
              <VBtn
                variant="tonal"
                prepend-icon="tabler-menu-2"
                @click="isLeftSidebarOpen = true"
              >
                {{ t('calendar.filters') }}
              </VBtn>
            </div>
            <FullCalendar
              ref="calendarRef"
              :options="options"
            />
          </VCard>
        </VMain>
      </VLayout>
    </VCard>
  </div>
</template>

<style lang="scss">
@use "@core/scss/template/libs/full-calendar";

.calendars-checkbox {
  .v-label {
    color: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
    opacity: var(--v-high-emphasis-opacity);
  }
}

.calendar-add-event-drawer {
  &.v-navigation-drawer:not(.v-navigation-drawer--temporary) {
    border-end-start-radius: 0.375rem;
    border-start-start-radius: 0.375rem;
  }

  &.v-navigation-drawer--temporary:not(.v-navigation-drawer--active) {
    transform: translateX(-110%) !important;
  }
}

.calendar-date-picker {
  display: none;

  +.flatpickr-input {
    +.flatpickr-calendar.inline {
      border: none;
      box-shadow: none;

      .flatpickr-months {
        border-block-end: none;
      }
    }
  }
}
</style>

<style lang="scss" scoped>
.v-layout {
  overflow: visible !important;

  .v-card {
    overflow: visible;
  }
}
</style>
