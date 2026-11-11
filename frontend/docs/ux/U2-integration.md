# U2 接入说明

> **历史记录：** 2026-11-11。本文保留当时结论；现行规范见 [前端开发规范](../前端开发规范.md) 和 [对接真实接口](../对接真实接口.md)。


本任务在保留首页只读聚合 API 和服务层范围裁剪的基础上，补齐 D01 的已登录用户入口标记、根路径重定向、店铺主数据绑定和手动新人引导入口。经营数据仍由 `report:read` 单独控制，不会因为能打开首页而新增数据权限。

## 顶栏入口（由 U1 接入）

如果需要在顶栏或用户菜单增加统一入口，请复用首页的 `useOnboardingTour`，不要在布局层复制 Shepherd 实例：

```ts
import { useOnboardingTour } from '@/components/tour/useOnboardingTour'

useOnboardingTour().restart()
```

该入口应只调用 `restart()`，引导步骤会根据当前角色在 DOM 中可见的侧栏 href 自动筛选。无需给导航项添加新的 `data-*` 属性；如果未来导航组件改为不输出稳定 href，需要在导航侧保留 `a[href="/dashboard/todos"]` 这一选择器契约，或由整合者统一调整 `useOnboardingTour.ts` 的 `menuSelector`。

## 首页 API 契约

`src/api/home.ts` 只编排现有的 `dashboard`、`approvals`、`scoped-reads` API 和新增的当前会话范围读取函数。待办、审批和提醒在服务层按 `userId`、审批权限和 C 批 scope 引擎裁剪；经营总览在服务层按当前角色允许的店铺集合裁剪。每个读取板块独立处理无权限异常，页面收到空数组或 `undefined` 时自动隐藏该板块。若后端替换 mock API，应保持这些权限断言和 scope 裁剪契约；不应从首页直接访问数据库或员工工资接口。

## 不可见菜单步骤

引导在初始页面检查侧栏 href；角色不可见 `/dashboard/todos` 时，会同时跳过“侧栏”和“跨页待办”两步。整合布局时请保留默认 Vuexy 垂直导航的链接 DOM。

## 本轮接入结果

D01 通过 `authenticated: true` 声明任何已登录角色可访问；路由守卫和菜单生成均识别该标记，未登录仍跳转 `/login`，其他页面权限逻辑保持原样。根路径使用独立 `/` 重定向记录，避免 `setupLayouts` 生成的空首页子路由抢先匹配。

首页新人引导不再自动启动，页面保留“重新开始引导”按钮；Shepherd 多步和跨页定义继续按可见菜单筛选。`frontend/scripts/verify-home-access.ts` 覆盖旧五角色与十六个模板角色的首页访问、菜单、范围读取、工资字段和经营指标权限。4222 preview 的现场截图保存在 `C:\Users\cimi\AppData\Local\Temp\cx-pw\par_home\`。
