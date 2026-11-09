# 批次 C 权限与页面访问复核

日期：2026-11-10（Asia/Shanghai）

## 页面与角色访问

页面目录共 226 页：旧页面 128 页、新批次页面 98 页。所有页面都通过 `page()` 生成页面级 `requiredPermissions`；公开页使用空数组，非公开页缺少声明时由页面分组映射到明确的 ERPNext DocType / Odoo 模型权限点，`canRoleOpen()` 对空声明默认拒绝。

`pnpm exec tsx scripts/check-gap-c-permissions.ts` 的访问数量输出如下（旧页不含公开页；新页为 98 页）：

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
- `dataScopesFor(subject, permissionKey)` 与 `scopeAllows(subject, permissionKey, ownerId, department)`（由 `gapCReadHelpers` 导出）：服务查询先按数据范围裁剪，再返回字段裁剪后的记录。
- `requireActorPermission(actor, permissionKey)` / `actorCan(actor, permissionKey)`：供 `src/mocks/services` 直接调用；`src/api` 使用 `assertPermission()`，显式拒绝时抛错。

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
