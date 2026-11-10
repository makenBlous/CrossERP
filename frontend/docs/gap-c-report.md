# 批次 C 权限与页面访问复核

日期：2026-11-10（Asia/Shanghai）

## 页面与角色访问

页面目录共 227 页：旧页面 128 页、新批次页面 99 页。新增 `/me/data-scope`「我的数据范围」页面，所有登录角色均可打开。所有页面都通过 `page()` 生成页面级 `requiredPermissions`；公开页使用空数组，非公开页缺少声明时由页面分组映射到明确的 ERPNext DocType / Odoo 模型权限点，`canRoleOpen()` 对空声明默认拒绝。

`pnpm exec tsx scripts/check-gap-c-permissions.ts` 的访问数量输出如下（旧页不含公开页；新页为 99 页）：

| 角色 | 旧页 | 新页 |
|---|---:|---:|
| admin | 124 | 97 |
| operator | 96 | 16 |
| finance | 53 | 23 |
| viewer | 53 | 12 |
| auditor | 23 | 12 |
| owner_manager | 124 | 98 |
| operations_manager | 70 | 23 |
| store_operator | 70 | 20 |
| advertising | 36 | 9 |
| product_developer | 35 | 11 |
| purchaser | 38 | 17 |
| warehouse_logistics | 22 | 5 |
| customer_service | 46 | 9 |
| accountant | 50 | 25 |
| finance_manager | 50 | 32 |
| cashier | 32 | 11 |
| hr_admin | 9 | 28 |
| employee | 9 | 20 |
| department_manager | 17 | 21 |
| auditor_template | 122 | 65 |
| external_viewer | 41 | 16 |

旧五角色的 128 页非公开访问结果与 `%TEMP%\\cx-pw\\b0_base_pages.json` 一致。新模板没有继承旧角色映射；老板模板可访问用户、角色和权限矩阵，审计模板可只读角色与权限矩阵但不能管理用户，其余模板默认拒绝这些系统管理页面。普通员工不能打开 `/finance/vouchers`，但可访问自己的报销、请假、工资条、通知、知识库和新人上手页面。

## 权限契约

其他批次必须在服务层复用以下函数，页面上的隐藏按钮不能替代服务校验：

- `canPermission(subject, permissionKey)`：判断当前用户有效权限；权限合并后显式 `deny` 优先，临时授权按 `startsAt` / `expiresAt` 计算。
- `fieldAccess(subject, fieldKey)`：返回 `hidden`、`masked`、`readonly` 或 `visible`。mock 返回数据前调用 `projectGapCField()`，隐藏字段删除，脱敏字段替换为 `***`。
- `computeEffectivePermissions()` / `effectivePermission()`：读取来源、拒绝来源和数据范围；不要读取 `legacyRoleMap` 给新模板放大权限。
- `dataScopesFor(subject, permissionKey)`、`shopsForSubject(subject)` 与 `scopeAllows(subject, permissionKey, ownerId, department, shopId)`（由 `gapCReadHelpers` 导出）：服务查询先按数据范围裁剪，再返回字段裁剪后的记录。
- `requireActorPermission(actor, permissionKey)` / `actorCan(actor, permissionKey)`：供 `src/mocks/services` 直接调用；`src/api` 使用 `assertPermission()`，显式拒绝时抛错。

### 数据范围语义

| 范围 | 允许条件 | 记录缺少关联字段时 |
|---|---|---|
| 本人（`self` / `owner`） | `ownerId === subject.userId` | 只要有本人 `ownerId` 即可判断；缺少则拒绝 |
| 部门（`department`） | 记录 `department` 存在且等于主体部门 | 拒绝 |
| 店铺（`store`） | 记录 `shopId` 存在且属于 `shopsForSubject(subject)` | 拒绝 |
| 全公司（`all`） | 直接允许 | 允许；这是明确的全公司授权 |

同一权限的多个范围按并集计算，任一范围命中即可允许；范围为空或含未实现的未知范围时一律拒绝。店铺绑定目前只存在于 C 批次 mock 配置，并不代表真实后端用户与店铺关联表。

权限 key 使用 `DocType/模型:动作`，例如 `expense_claim:read`、`journal_entry:read`、`employee_record:read`、`report:read`；字段权限使用 `对象.字段:动作`。人事和 D 批次共用以下 key：`employee.salary:read`、`employee.id_number:read`、`salary_slip:read_own`、`salary_slip:read_all`、`employee_record:read_own`。普通员工只授予 `salary_slip:read_own`（数据范围 `self`），人事模板授予员工薪资与证件字段权限；其他角色默认隐藏或脱敏。

## 验收脚本输出

```text
gap-c permission checks passed
```

脚本还断言页面总数、非公开页面权限声明、旧角色基线、系统管理页默认拒绝、员工凭证页拒绝、显式拒绝优先和临时授权到期失效。

## 检查命令

- `pnpm exec tsx scripts/check-gap-c-permissions.ts`：通过。
- `pnpm run typecheck`：通过。
- `node_modules/.bin/eslint.cmd . -c .eslintrc.cjs --ext .ts,.js,.cjs,.vue,.tsx,.jsx`：0 error（保留既有 42 条 warning）。
- `pnpm run build`：通过，Vite 输出 `✓ built`。

真实后端 API、数据库权限账号和审计链仍由后续批次接入；ERPNext/Odoo 标注“未核实”的名称继续保留原标记。

## 批次 C 第三轮权限地基修复（2026-11-10）

- 旧角色的数据范围现在随有效权限写入：`admin`、`finance`、`auditor` 为 `all`，`operator` 为 `store + owner`，`viewer` 为 `store`。因此旧角色的 `allowed` 权限不会再出现空 `dataScopes` 导致的假拒绝。
- `admin` 按 02 设计中“老板/总经理”的默认字段限制“无”处理：这是基于模板语义的**推断**，因此成本、毛利、薪资、证件和银行卡字段均可见。`owner_manager` 与旧 `admin` 的成本/毛利结果一致。
- `finance` 按 02 设计中“会计/财务覆盖全部财务数据”的**推断**开放 SKU 成本和毛利；薪资、证件、银行卡仍没有字段权限，继续隐藏。财务角色不因此获得员工档案敏感字段。
- `scoped-reads.ts` 不再按 `department_manager` 角色名判断部门范围，只依据 `effectivePermission(...).dataScopes`；店铺范围要求记录带有 `shopId` 且命中主体的模拟店铺绑定，缺少店铺字段一律拒绝。
- 普通员工按 02 设计“我的个人档案”获得本人一条员工记录；接口选择 `employee_record:read_own`，并继续按字段权限删除薪资、证件和银行卡。对 `employee_record:read` 的显式拒绝优先于本人范围授权，返回空结果。

第三轮验收摘要：

- 独立 `xperm.ts`：`== FAIL 0`；旧五角色旧页面基线差异 `0`。
- 独立 `xperm2.ts`：`== FAIL 0`；旧 admin 成本/毛利 `visible/visible`，员工本人档案条数 `1`，finance 报销条数 `2`。
- `gap-c-scoped-reads.ts`：`gap-c scoped mock reads passed`。

## 批次 C 缺口补齐记录（2026-11-10）

本轮把独立权限实测发现的 16 项失败收敛为 0 FAIL，并保留旧五角色的 128 页基线。旧角色的 `:read` 泛授已排除字段权限和敏感权限点；工资、工资明细、证件号、银行账号、SKU 成本、SKU 毛利和买家联系方式统一登记到敏感字段权限表。财务、运营、只读和旧审计角色默认隐藏这些字段；人事模板显式授予薪资与证件字段；普通员工仍只拥有本人范围的工资条。部门主管增加 `employee_record:read` 的本部门范围。审计模板保留权限配置只读查看、报表和日志导出，没有写权限，也不能打开工资或员工档案敏感页；外部顾问只读报表和通知。

静态原型缺口已由 API/mock 与页面共同补齐：

- SYS21 在现有角色页提供「复制并保存角色」，保存父角色继承、欧洲店铺/部门/本人范围、用户指派和审计记录；页面提示菜单和数据范围会按新角色刷新，真实后端角色表仍未接入。
- RP03 提供订单、报销、员工档案、审计日志四类模拟数据源，字段多选和筛选可保存；保存后立即运行并展示模拟结果，数字来自 mock 数据。
- U08 可保存保留策略并执行「模拟归档」，只追加执行记录，不删除审计日志；真实文件归档仍未接入。
- SYS22 保存前显示预计影响用户数，敏感权限仍要求另一位管理员确认；保存结果进入权限变更记录。
- 订单、报销和员工档案新增范围裁剪读接口：部门主管只拿运营部，员工只拿本人，无权限角色得到空结果或服务层拒绝；敏感字段在返回前删除或脱敏。
- SYS23 增加「当前身份可见数据预览」，并新增 `/me/data-scope`：两页复用 `ScopedDataPreview`，调用订单、报销、员工档案三个 scoped read API 和当前主体上下文，展示数据范围、绑定店铺和每条记录的 `shopId` / `ownerId` / `department`；接口拒绝的表按空结果展示「当前主体无读取权限」，员工敏感字段仍由接口投影裁剪，顶栏角色切换后重新加载。
- `scripts/check-gap-c-own-scope.ts` 静态检查零参数页面/API 签名，并逐角色比对 scoped API 与 `listScoped*` 的主体范围结果及 admin 子集关系。

审计依据：`docs/design/06-补齐开发批次.md` 第 3 节列出的批次 C 流程，及 `docs/design/01-前端页面设计.md` 第 20.11 节的 16 个预置模板。真实后端、真实文件存储、外部通知渠道和数据库账号权限仍未验证。

点击验收脚本位于 `C:\Users\cimi\AppData\Local\Temp\cx-pw\gap-c-flows\flows.js`，结果写入同目录 `result.json`；本次 AI 正常/关闭各 10 条流程，共 20/20 通过。

## 批次 C 第五轮店铺范围修复（2026-11-10）

- `scopeAllows()` 保持四参数调用兼容，并增加可选 `shopId`；`all` 明确放行，`store` 只匹配主体绑定店铺，`self`/`owner` 按 `ownerId`，`department` 按主体部门；多个范围取并集。
- 空范围、未知范围、缺少 `shopId` 或缺少部门时拒绝；`shopsForSubject()` 的绑定是 C 批次模拟配置，旧 `viewer`、`operator` 至少绑定一个店铺，`external_viewer` 只绑定少量店铺。
- 订单 fixture 为 3 条、覆盖 3 个店铺且每条带 `shopId`；报销和员工档案 fixture 也带店铺关联，所有 scoped read 调用传入 `shopId`。
- 独立 `xperm.ts`、`xperm2.ts`、`xperm3.ts` 均为 `== FAIL 0`；`check-gap-c-permissions.ts`、`gap-c-scoped-reads.ts`、`check-legacy-read-apis.ts`、typecheck、ESLint（0 errors）和 build 均通过。
