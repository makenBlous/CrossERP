# CrossERP 前端静态原型

这是 CrossERP 的浏览器静态原型。页面使用假数据，不连接后端。用来确认菜单、角色和主要页面长什么样。

Vuexy 是商业模板。定制后的 `frontend/` 不要放进公开仓库，除非许可证允许。详见仓库 `docs/design/00-总览.md`。

## 环境要求

- Node.js 20 或以上
- pnpm（本目录已有 `pnpm-lock.yaml`，不要改用 npm 或 yarn）

## 启动

在 `frontend/` 目录执行：

```bash
pnpm install
pnpm dev
```

浏览器打开终端里打印的本地地址。默认语言是简体中文，顶栏可以切换 English，也可以切换明暗主题。

生产构建：

```bash
pnpm build
```

类型检查：

```bash
pnpm run typecheck
```

## 登录和角色

登录页任意输入即可进入。密码不会写入存储。

顶栏角色切换器有五种角色：管理员、运营、财务、只读、审计。切换后左侧菜单按 `src/config/pages.ts` 里的可见角色过滤。直接打开无权限地址会进入 `/not-authorized`。

## 目录

- `src/config/pages.ts`：全部页面配置。菜单和占位页都从这里生成。
- `src/mocks/`：按领域拆开的假数据。
- `src/api/`：页面调用的薄封装，返回 `Promise`。
- `src/pages/`：已经做成静态页的路由。没有单独 `.vue` 文件的地址由占位页渲染。
- `src/plugins/i18n/`：中文和英文文案。

## 怎么加一个页面

1. 在 `src/config/pages.ts` 增加一条记录：路径、中英文名称、分组、图标、可见角色、目的、主要区块、阶段。
2. 若要出现在左侧菜单，把 `showInMenu` 设为 `true`，并指定 `group`。
3. 还没做界面时不用新建 `.vue`。路由会指向占位页，显示名称、目的、计划区块和阶段。
4. 要做成真实静态页时，在 `src/pages/` 按路径建文件，并把该条的 `implemented` 设为 `true`。
5. 中英文菜单名来自配置。页面里的句子写进 `src/plugins/i18n/ui.ts` 的两种语言。

## 假数据换成 `/api/v1`

页面只调用 `src/api/` 下的函数，不直接读 `src/mocks/`。

以后把这些函数改成请求 `/api/v1`，返回类型保持不变，页面不用改。例如 `fetchOrders()` 现在是 `readMock(orderSummaries)`，以后换成对 `GET /api/v1/sales/orders` 的请求即可。

金额在假数据里已经算好。页面只展示，不在浏览器里重算利润或改写匹配结果。

## 许可证提醒

界面骨架来自 Vuexy 商业后台模板。不要把 `frontend/`、模板源码或商业图片提交到公开仓库。本原型只供内部演示。
