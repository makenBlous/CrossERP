import type { HorizontalNavItems, VerticalNavItems } from '@layouts/types'
import { canRoleOpen, menuGroups, pageCatalog } from '@/config/pages'
import type { Role } from '@/types/domain'
import { useMockDbStore } from '@/stores/mockdb'

export function buildNav(role: Role): VerticalNavItems {
  const db = useMockDbStore()
  const override = db.db.roleOverrides?.find(item => item.role === role)

  return menuGroups.flatMap(group => {
    const groupHidden = Boolean(override?.hiddenGroups.includes(group.id))

    const children = pageCatalog
      .filter(item => item.showInMenu && item.group === group.id && canRoleOpen(role, item) && (item.id === 'D01' || (!groupHidden && !override?.hiddenPageIds.includes(item.id))))
      .map(item => ({
        title: `page.${item.id}.name`,

        // Vuexy 把字符串 to 当作路由名；这里用路径对象，兼容文件路由与占位路由
        to: { path: item.path },
        icon: { icon: item.icon },
      }))

    if (!children.length)
      return []

    return [{
      title: `menu.${group.id}`,
      icon: { icon: group.icon },
      children,
    }]
  })
}

export function buildHorizontalNav(role: Role): HorizontalNavItems {
  return buildNav(role) as HorizontalNavItems
}
