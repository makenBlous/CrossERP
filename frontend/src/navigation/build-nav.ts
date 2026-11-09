import type { HorizontalNavItems, VerticalNavItems } from '@layouts/types'
import { menuGroups, pageCatalog } from '@/config/pages'
import type { Role } from '@/types/domain'

export function buildNav(role: Role): VerticalNavItems {
  return menuGroups.flatMap(group => {
    const children = pageCatalog
      .filter(item => item.showInMenu && item.group === group.id && item.roles.includes(role))
      .map(item => ({
        title: `page.${item.id}.name`,
        to: item.path,
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
