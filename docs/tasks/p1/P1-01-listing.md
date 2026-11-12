# 平台 Listing（P1-01-listing）

- **旧任务卡：** TASK-p1-cat-listing、-nodef（仓库外）
- **状态：** 已合入 main（0a7db9b、3c34471、b6c8866）
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

商品主数据的平台 Listing部分，见 [P1-01 功能包](P1-01-catalog.md)。

## 范围：接口与迁移

`GET /catalog/listings`、`GET /catalog/listings/{id}`、`POST /catalog/listings`、`PATCH /catalog/listings/{id}`（负责人、状态）、`POST /catalog/listings/status`。 路由 `src/crosserp/api/routers/catalog_*.py`，服务 `src/crosserp/catalog/`。

## 依赖

P0 全部。

## 必须复用的共用函数

见 [rules.md](../rules.md) 第 3 节。本功能重点：`PermissionService.store_scope` + `apply_store_scope`（店铺范围）、`make_action_dispatcher`（写动作）、`api_endpoint(..., idempotency="dispatcher")`（写接口幂等归属）、`ApprovalGateway.submit` → `ApprovalSubmission`（高风险）、`AuditRecorder`（工厂注入）、dispatcher 撤销登记（中风险）。

## 验收标准（逐条可测试）

1. 按店铺范围过滤；店铺 A 的用户看不到店铺 B 的 Listing（有测试）。
2. 有权调用返回 200，列表真正分页切片，`q`/`sort` 按草案实现。
3. 无权限点返回 404（不是 403），不存在的 id 返回 404，未登录返回统一 401 错误体。
4. 店铺/数据范围：列表只返回范围内数据（用 `store_scope` + `apply_store_scope`），范围外单条 404；空范围返回空列表。
5. 金额字段为 `Money{amountMinor,currency}` 万分位整数，无浮点；字段权限按 `PermissionService.serialize`。
6. 写动作经 `make_action_dispatcher(session, permission_service)` 在请求事务里派发；`api_endpoint` 声明 entity/action/permission/riskTier/idempotency 与 OpenAPI 草案一致。
7. 范围外写返回 403 `DATA_SCOPE_DENIED`；无权 404；未登录 401。
8. AI 按风险档：medium 直接执行并写 `agent_undo` 撤销记录（且有一条"撤销成功"测试）；high 只生成审批，审批前业务数据不变；critical AI 拒绝。人发起 high 按 ApprovalSubmission 的 `required/auto_effective/awaiting_initiator` 处理，不能自批。
9. 幂等：同人同键同体回放原响应；同键不同体 409；他人同键不可见（无权 404）；未登录同键 401 不回放；权限收回后回放 404。
10. `expectedVersion` 冲突返回 409，不覆盖。
11. 审计记录含 `actor_type`、`on_behalf_of`、`request_id`；AI 发起时含 agent 字段。
12. 请求结束后用全新 Session 能查到写入结果（真实提交）。
13. `check_merge_guard.py --base <切出点>` 0 命中，或命中已在验收报告中逐条豁免。
14. 独立验收报告 `<块>-accept.txt` 结论为"通过"，横向对比无不一致项。
15. rules.md 第 5 节全部检查 0 失败（SQLite 全量、MySQL `-m db`、双库迁移往返、ruff、mypy、文档链接、授权覆盖、API contract、密钥扫描）。

## 进度

已合入，见状态。合并记录以 `git log --first-parent main` 为准。

## 待定 / 需拍板

无。
