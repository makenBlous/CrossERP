# 补齐批次 C 验收报告

日期：2026-11-10（Asia/Shanghai）

## 页面清单

已将 21 个批次 C 路由从占位页替换为可交互静态页面：

- 审批：W05 智能体建议、W06 抄送我的、W07 审批规则与额度。
- 协作：N01 消息中心、N02 我的订阅、RP01 报表中心、RP02 报表查看、RP03 自定义报表。
- 审计：U05 AI 操作日志、U06 建议追溯、U07 敏感操作告警、U08 日志保留与归档。
- 权限：SYS14 字段权限、SYS15 数据范围、SYS16 临时授权、SYS17 权限复核、SYS18 职责分离、SYS21 角色详情、SYS22 权限矩阵、SYS23 有效权限查看、SYS24 权限变更记录。

页面统一使用 `ListPage`、`DetailPage`、`MoneyText`、`PermissionGate`、Vuetify 表单和时间线；数据均通过 `src/api/gap-c.ts` 进入批次 C mock 服务。

## 流程结果

Playwright 脚本：`%TEMP%\cx-pw\gap-c\gap_c_flow.js`，截图：`%TEMP%\cx-pw\gap-c\shots\`。

- 统一审批：智能体建议页点击“批准”成功，服务层拒绝自审批。
- 通知订阅：修改并保存订阅成功。
- 报表：选择期间并运行预算报表成功，结果由 API 返回。
- 临时授权：创建 7 天授权成功，返回状态可按到期时间计算。
- 权限矩阵：敏感权限填写另一位管理员后保存成功。
- AI 关闭：设置 `crosserp-ai-mode=off` 后人工审批页仍可打开，助手抽屉隐藏。
- 批次 C smoke：5 个角色（admin、finance、operator、employee、auditor）逐页打开 21 页，105 次访问均为 0 控制台错误；管理员 21/21 页面打开，其他角色按有效权限被放行或拦截。

旧角色回归使用 `BASE=http://127.0.0.1:4183 node %TEMP%\cx-pw\b0_reg.js`。5 个旧角色均为 0 控制台错误，访问结果与 `b0_base_reg.json` 的既有基线一致；基线自身在 SKU 利润详情页保留 1 个内容长度告警，本批未新增该告警。

## 权限与数据安全

- 新模板不再通过 `legacyRoleMap` 借用旧角色权限；权限引擎覆盖继承、多角色并集、显式拒绝优先、临时授权到期和 AI 收窄。
- 旧角色动作 `update` 与权限点 `write` 已兼容映射，管理员原有页面访问不变。
- mock 服务写操作统一检查有效权限；字段权限和数据范围在返回数据前裁剪，敏感权限矩阵保存要求第二位管理员确认。
- `frontend/scripts/check-gap-c-permissions.ts` 已运行并输出 `gap-c permission checks passed`。

## 检查命令

- `pnpm install --frozen-lockfile --prefer-offline`：通过。
- `pnpm run typecheck`：通过。
- `pnpm exec eslint . -c .eslintrc.cjs --ext .ts,.js,.cjs,.vue,.tsx,.jsx`：0 error（保留既有 25 条 Vue 格式 warning）。
- `pnpm run build`：通过，Vite 输出 `✓ built`。

## 未完成项与未核实项

- 本批仍是静态前端，真实 `/api/v1`、后端权限表和数据库审计链尚未接入。
- ERPNext/Odoo 对照名称中设计文档标注“未核实”的部分继续保留原标注。
- 旧基线已有的 SKU 利润详情内容长度告警未扩大范围处理。
