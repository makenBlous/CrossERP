# U2 接入说明

本任务只改动个人首页、首页只读聚合 API、引导组件和验证脚本，没有改动公共路由、布局、权限、会话或 i18n 文件。

## 顶栏入口（由 U1 接入）

如果需要在顶栏或用户菜单增加统一入口，请复用首页的 `useOnboardingTour`，不要在布局层复制 Shepherd 实例：

```ts
import { useOnboardingTour } from '@/components/tour/useOnboardingTour'

useOnboardingTour().restart()
```

该入口应只调用 `restart()`，引导步骤会根据当前角色在 DOM 中可见的侧栏 href 自动筛选。无需给导航项添加新的 `data-*` 属性；如果未来导航组件改为不输出稳定 href，需要在导航侧保留 `a[href="/dashboard/todos"]` 这一选择器契约，或由整合者统一调整 `useOnboardingTour.ts` 的 `menuSelector`。

## 首页 API 契约

`src/api/home.ts` 只编排现有的 `dashboard`、`approvals`、`scoped-reads` API。每个读取板块独立处理无权限异常，页面收到空数组或 `undefined` 时自动隐藏该板块。若后端替换 mock API，应保持这些现有 API 的权限断言和 scope 裁剪契约；不应从首页直接访问数据库或员工工资接口。

## 不可见菜单步骤

引导在初始页面检查侧栏 href；角色不可见 `/dashboard/todos` 时，会同时跳过“侧栏”和“跨页待办”两步。整合布局时请保留默认 Vuexy 垂直导航的链接 DOM。

## 已发现的接入阻塞

当前 `src/config/pages.ts` 的 D01 `/dashboard` 条目没有 `requiredPermissions`。现有路由守卫对非旧五角色会因此拒绝 D01，所以 `employee`、`customer_service` 等模板角色直接深链 `/dashboard` 会落到 `/not-authorized`，无法完成首页验收。该文件属于公共文件，本任务没有直接修改；整合时请为 D01 补充与现有首页 API 一致的只读权限（建议 `report:read` 或按板块拆分并允许空板块），并确认不扩大数据范围。修复后可复用本任务的 Playwright 脚本重跑全部角色截图。
