# CrossERP 前端

> **适用范围：** `frontend/` 浏览器端。**状态：** 仅静态原型（前端 mock）。页面和交互已在代码中实现；后端 JSON 接口仍处于设计阶段。

CrossERP 前端是 Vue 3 + TypeScript + Vite 的业务原型，使用 Vuetify 和 Vuexy 的页面结构。当前所有业务数据来自固定种子和浏览器本地 mock 数据库，未连接 CrossERP 后端。真实接口接入以 [前端开发规范](./docs/前端开发规范.md) 和 [对接真实接口](./docs/对接真实接口.md) 为准。

## 技术栈与边界

- Vue 3、TypeScript、Vite、Vue Router auto routes、Pinia。
- Vuetify 3 与 Vuexy full-version 的页面结构和可复用组件。
- `vue-i18n` 提供中文和英文文案；页面不直接访问 mock 数据。
- 业务操作由确定性 TypeScript 代码完成，金额使用 `Minor` 万分位整数；AI 只读已存储结果，写操作最多形成待审批建议。
- 后端沿用 Python / FastAPI 的设计，但目前只存在接口草案和 service 注释，前端运行不需要后端。

## 目录与事实来源

| 目录或文件 | 用途 |
|---|---|
| `src/config/pages.ts` | 唯一页面目录 `pageCatalog`、菜单分组、路由路径、阶段、实现状态、角色和页面权限点。当前目录有 238 个页面 ID，其中 151 个标记为已实现，113 个显示在菜单中。 |
| `src/config/permissions.ts` | 权限点目录、角色模板、旧角色兼容映射。 |
| `src/plugins/1.router/` | 自动路由包装、占位路由和权限守卫；无权限地址进入 `/not-authorized`。 |
| `src/navigation/` | 按 `pageCatalog` 和当前角色生成侧栏菜单。 |
| `src/pages/` | 路由页面；没有独立页面文件的目录项由 `PlaceholderPage` 渲染。 |
| `src/components/biz/`、`src/views/` | 可复用业务壳和批次视图，如 `ListPage`、`DetailPage`、`FormDrawer`、`MoneyText`。 |
| `src/api/` | 页面唯一调用入口。函数签名和返回类型是未来真实接口的适配边界。 |
| `src/mocks/seed/`、`src/mocks/services/` | 固定种子、内存数据流转和 mock 业务服务；仓库没有独立的 `src/services/` 目录。 |
| `src/stores/mockdb.ts` | Pinia 内存数据库，并持久化到 `localStorage` 的 `crosserp-mockdb-v1`。 |
| `src/agent/`、`src/components/chat/`、`src/components/biz/AssistantDrawer.vue` | 当前 `MockAgentAdapter`、聊天历史和全局助手。 |
| `src/utils/money.ts` | `Minor` 解析、加减、汇率演示换算和展示舍入。 |
| `src/types/` | 页面和领域类型；金额字段逐步迁移到 `Minor`，HR 旧的 `*Cents` 由真实接口接入时统一。 |

页面来源和 Vuexy 复用记录见 [组件复用审计](./docs/component-reuse-audit-final.md)、[复用审计明细](./docs/component-reuse-audit.md) 和 [第三批页面来源](./docs/vuexy-sources-batch3.md)。

## 本地运行与构建

环境要求：Node.js 20 或以上，pnpm。安装依赖：

```powershell
cd frontend
pnpm install
pnpm dev
```

开发服务器端口由 Vite 配置决定。主人预览使用 4173；不要把 5173 当作本项目预览端口。

Windows 构建使用仓库已安装的 Vite 二进制：

```powershell
cd frontend
node node_modules\vite\bin\vite.js build
```

构建可能改写 `auto-imports.d.ts`、`components.d.ts`、`typed-router.d.ts`。验证构建后必须还原这 3 个声明文件，再提交文档或代码变更。只看效果时使用 4173 预览端口；本任务不要求启动预览服务器。

## 登录、角色与权限

静态登录页接受任意输入，仅把显示名写入会话存储；密码不会保存。角色切换对应独立演示身份，当前角色影响菜单、页面守卫和服务层权限判断。页面级权限来自 `pageCatalog` 的 `requiredPermissions` / `requiredAnyPermissions`；按钮级权限使用 `PermissionGate` 或 `v-can`，服务层仍通过 `assertPermission` 再检查。

登出会清理会话并整页跳转到登录页。真实环境以 `GET /api/v1/auth/me` 返回的用户、角色、有效权限点和数据范围为唯一来源，前端判断只用于改善体验。

## AI 开关与人工兜底

`useAiModeStore` 提供正常、降级、关闭三种模式。关闭 AI 时，`App.vue` 不挂载全局 `AssistantDrawer`，业务页面仍可使用人工表单、提交和审批流程；降级模式只允许只读查询。助手适配器当前是 `MockAgentAdapter`，只读取 mock 数据中的订单、SKU、采购、物流、利润和异常等已存储结果。建议卡调用 `submitAgentSuggestion` 进入待审批记录，不直接改金额、库存或凭证。

聊天请求在登出、切换用户或切换角色时由 `useChatInflight` 使旧请求失效，旧回调不能写入新会话；登出还会整页刷新到登录页。未登录或 AI 关闭时不显示浮动助手。模型设置的目标界面只保留 `baseUrl`、`apiKey`、`model` 三项；`apiKey` 必须加密存储、不回显、不写日志。当前仓库没有把该真实模型配置接通，属于设计约束。

## 数据与业务约束

- 金额在服务层用 `Minor`（万分位整数）计算，页面只格式化展示；不要用 `float` 做金额运算。
- mock 数据重置由 `buildSeed()` 生成固定种子，状态通过 `useMockDbStore` 保存；列表视图设置单独保存在浏览器中。
- 所有页面通过 `src/api/` 调用数据。将来切换真实接口时保持函数名、参数和返回类型，页面组件不改。
- 审批、审计和职责分离仍由服务层决定。AI 不能直接写账；审批按钮旁应明确显示审批人、是否提交即生效以及是否需要发起人确认。
- 不提供通行证管理 UI。委托通行证由服务端自动签发、静默续期并在登出、切换账号、权限变化、停用或关闭 AI 时作废，用户无需操作。

## 继续阅读

- [前端文档索引](./docs/README.md)
- [前端开发规范](./docs/前端开发规范.md)
- [对接真实接口](./docs/对接真实接口.md)
- [页面设计总览](../docs/design/01-前端页面设计.md)
