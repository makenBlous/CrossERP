# 我的账户：资料、改密码、API Token、我的会话（P0-01-account）

- **旧任务卡：** TASK-pf-account（仓库外）
- **状态：** 已合入 main（3fd08b9–2fd57d3）
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

用户自助管理资料、密码、API Token 和会话。

## 范围：接口与迁移

`src/crosserp/api/routers/account.py` 中的账户接口（以 OpenAPI 草案 platform 分组为准）。

## 依赖

P0-01-auth。

## 必须复用的共用函数

见 [rules.md](../rules.md) 第 3 节。本功能重点：`PermissionService.store_scope` + `apply_store_scope`（店铺范围）、`make_action_dispatcher`（写动作）、`api_endpoint(..., idempotency="dispatcher")`（写接口幂等归属）、`ApprovalGateway.submit` → `ApprovalSubmission`（高风险）、`AuditRecorder`（工厂注入）、dispatcher 撤销登记（中风险）。

## 验收标准（逐条可测试）

1. Token 明文只返回一次、库里只存哈希；吊销后 Bearer 立即 401。
2. 只能看/踢自己的会话，踢别人的 404；改密码后其他会话失效。
3. 改资料不能改用户名、角色等越权字段；AI principal 调 critical 写接口被拒。
4. 写操作有审计和 security_event。
5. 写动作经 `make_action_dispatcher(session, permission_service)` 在请求事务里派发；`api_endpoint` 声明 entity/action/permission/riskTier/idempotency 与 OpenAPI 草案一致。
6. 范围外写返回 403 `DATA_SCOPE_DENIED`；无权 404；未登录 401。
7. AI 按风险档：medium 直接执行并写 `agent_undo` 撤销记录（且有一条"撤销成功"测试）；high 只生成审批，审批前业务数据不变；critical AI 拒绝。人发起 high 按 ApprovalSubmission 的 `required/auto_effective/awaiting_initiator` 处理，不能自批。
8. 幂等：同人同键同体回放原响应；同键不同体 409；他人同键不可见（无权 404）；未登录同键 401 不回放；权限收回后回放 404。
9. `expectedVersion` 冲突返回 409，不覆盖。
10. 审计记录含 `actor_type`、`on_behalf_of`、`request_id`；AI 发起时含 agent 字段。
11. 请求结束后用全新 Session 能查到写入结果（真实提交）。
12. `check_merge_guard.py --base <切出点>` 0 命中，或命中已在验收报告中逐条豁免。
13. 独立验收报告 `<块>-accept.txt` 结论为"通过"，横向对比无不一致项。
14. rules.md 第 5 节全部检查 0 失败（SQLite 全量、MySQL `-m db`、双库迁移往返、ruff、mypy、文档链接、授权覆盖、API contract、密钥扫描）。

## 进度

已合入。

## 待定 / 需拍板

无。
