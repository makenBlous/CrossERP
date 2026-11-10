import Shepherd, { type Tour } from 'shepherd.js'
import 'shepherd.js/dist/css/shepherd.css'
import './onboarding.scss'
import { nextTick, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'

const seenKey = (role: string) => `crosserp-onboarding-tour-v1:${role}`

interface TourStepDefinition {
  id: string
  title: string
  text: string
  selector: string
  route?: string
  menuSelector?: string
  placement?: 'top' | 'bottom' | 'left' | 'right'
}

const steps: TourStepDefinition[] = [
  {
    id: 'welcome',
    title: '先看懂你的工作台',
    text: '这里汇总当前主体能读取的待办、提醒和业务摘要。金额和数据都来自已有权限 API。',
    selector: '#u2-home-welcome',
    placement: 'bottom',
  },
  {
    id: 'navigation',
    title: '从侧栏进入模块',
    text: '菜单按当前角色动态生成。引导只定位可见菜单，不会把不可见的页面展示给你。',
    selector: 'a[href="/dashboard/todos"]',
    menuSelector: 'a[href="/dashboard/todos"]',
    placement: 'right',
  },
  {
    id: 'todos',
    title: '跨页查看待办',
    text: '下一步会打开我的待办页，继续查看当前角色可处理的任务。',
    selector: 'main',
    route: '/dashboard/todos',
    menuSelector: 'a[href="/dashboard/todos"]',
    placement: 'bottom',
  },
  {
    id: 'shortcuts',
    title: '常用入口随手可达',
    text: '回到首页后，可以从这里进入订单、对账、日历等已有业务页面。',
    selector: '#u2-home-shortcuts',
    route: '/dashboard',
    placement: 'top',
  },
]

function waitForSelector(selector: string, timeout = 1800): Promise<Element | null> {
  if (typeof document === 'undefined')
    return Promise.resolve(null)

  const existing = document.querySelector(selector)
  if (existing)
    return Promise.resolve(existing)

  return new Promise(resolve => {
    const startedAt = Date.now()

    const poll = () => {
      const element = document.querySelector(selector)
      if (element || Date.now() - startedAt >= timeout) {
        resolve(element)

        return
      }
      window.setTimeout(poll, 40)
    }

    poll()
  })
}

function markSeen(role: string) {
  if (typeof localStorage !== 'undefined')
    localStorage.setItem(seenKey(role), '1')
}

function hasSeen(role: string) {
  return typeof localStorage !== 'undefined' && localStorage.getItem(seenKey(role)) === '1'
}

export function useOnboardingTour() {
  const router = useRouter()
  const route = useRoute()
  const session = useSessionStore()
  const currentTour = ref<Tour | null>(null)
  const isRunning = ref(false)

  function availableDefinitions() {
    return steps.filter(step => {
      const menuVisible = !step.menuSelector || Boolean(document.querySelector(step.menuSelector))
      const targetReady = Boolean(step.route) || Boolean(document.querySelector(step.selector))

      return menuVisible && targetReady
    })
  }

  function buildTour() {
    currentTour.value?.cancel()

    const tour = new Shepherd.Tour({
      useModalOverlay: true,
      defaultStepOptions: {
        cancelIcon: { enabled: true, label: '跳过新人引导' },
        classes: 'crosserp-onboarding-step',
        scrollTo: { behavior: 'smooth', block: 'center' },
      },
    })

    const available = availableDefinitions()

    available.forEach((definition, index) => {
      tour.addStep({
        id: definition.id,
        title: definition.title,
        text: definition.text,
        attachTo: { element: definition.selector, on: definition.placement ?? 'bottom' },
        beforeShowPromise: async () => {
          if (definition.route && route.path !== definition.route)
            await router.push(definition.route)

          await nextTick()
          await waitForSelector(definition.selector)
        },
        buttons: [
          {
            action: () => tour.back(),
            classes: 'shepherd-button-secondary',
            disabled: index === 0,
            text: '上一步',
          },
          {
            action: () => index === available.length - 1 ? tour.complete() : tour.next(),
            text: index === available.length - 1 ? '完成' : '下一步',
          },
        ],
      })
    })

    tour.on('show', () => {
      isRunning.value = true
    })
    tour.on('cancel', () => {
      isRunning.value = false
      markSeen(session.role)
    })
    tour.on('complete', () => {
      isRunning.value = false
      markSeen(session.role)
    })
    currentTour.value = tour

    return tour
  }

  async function start(force = false) {
    if (!force && hasSeen(session.role))
      return

    const tour = buildTour()
    if (!tour.steps.length)
      return

    await tour.start()
  }

  function restart() {
    void start(true)
  }

  function stop() {
    currentTour.value?.cancel()
  }

  onBeforeUnmount(stop)

  return { isRunning, restart, start, stop }
}
