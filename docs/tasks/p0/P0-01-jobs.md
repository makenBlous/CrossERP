# 后台任务与自调度 worker（P0-01-jobs）

- **旧任务卡：** TASK-pf-jobs（仓库外）
- **状态：** 已合入 main（285f7af）
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

定时任务由 CrossERP 自己调度（不依赖外部 cron），为导入、对账、摘要等提供后台执行。

## 范围：接口与迁移

`/tasks` 相关接口；`src/crosserp/api/routers/jobs.py` 与 worker。

## 依赖

P0-01 底座。

## 必须复用的共用函数

见 [rules.md](../rules.md) 第 3 节。本功能重点：`PermissionService.store_scope` + `apply_store_scope`（店铺范围）、`make_action_dispatcher`（写动作）、`api_endpoint(..., idempotency="dispatcher")`（写接口幂等归属）、`ApprovalGateway.submit` → `ApprovalSubmission`（高风险）、`AuditRecorder`（工厂注入）、dispatcher 撤销登记（中风险）。

## 验收标准（逐条可测试）

1. worker 领取任务互斥：两个 worker 不会领到同一任务。
2. 成功/失败状态与错误信息记录；未知任务类型显式失败。
3. 定时任务按配置周期入队（无外部 cron）。
4. 只能查看自己有权的任务，其他 404；worker 写操作审计 `actor_type=system`。
5. 有权调用返回 200，列表真正分页切片，`q`/`sort` 按草案实现。
6. 无权限点返回 404（不是 403），不存在的 id 返回 404，未登录返回统一 401 错误体。
7. 店铺/数据范围：列表只返回范围内数据（用 `store_scope` + `apply_store_scope`），范围外单条 404；空范围返回空列表。
8. 金额字段为 `Money{amountMinor,currency}` 万分位整数，无浮点；字段权限按 `PermissionService.serialize`。
9. 写动作经 `make_action_dispatcher(session, permission_service)` 在请求事务里派发；`api_endpoint` 声明 entity/action/permission/riskTier/idempotency 与 OpenAPI 草案一致。
10. 范围外写返回 403 `DATA_SCOPE_DENIED`；无权 404；未登录 401。
11. AI 按风险档：medium 直接执行并写 `agent_undo` 撤销记录（且有一条"撤销成功"测试）；high 只生成审批，审批前业务数据不变；critical AI 拒绝。人发起 high 按 ApprovalSubmission 的 `required/auto_effective/awaiting_initiator` 处理，不能自批。
12. 幂等：同人同键同体回放原响应；同键不同体 409；他人同键不可见（无权 404）；未登录同键 401 不回放；权限收回后回放 404。
13. `expectedVersion` 冲突返回 409，不覆盖。
14. 审计记录含 `actor_type`、`on_behalf_of`、`request_id`；AI 发起时含 agent 字段。
15. 请求结束后用全新 Session 能查到写入结果（真实提交）。
16. `check_merge_guard.py --base <切出点>` 0 命中，或命中已在验收报告中逐条豁免。
17. 独立验收报告 `<块>-accept.txt` 结论为"通过"，横向对比无不一致项。
18. rules.md 第 5 节全部检查 0 失败（SQLite 全量、MySQL `-m db`、双库迁移往返、ruff、mypy、文档链接、授权覆盖、API contract、密钥扫描）。

## 进度

已合入。

## 待定 / 需拍板

无。
