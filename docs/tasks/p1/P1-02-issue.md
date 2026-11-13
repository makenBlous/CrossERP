# 清洗问题处理与转交（P1-02-issue）

- **旧任务卡：** TASK-p1-ing-issue、-nodef、-nodef2（仓库外）
- **状态：** 已合入 main（`7ea9dfa`，合回 `498058c`）
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

数据进入链路的一部分，见 [P1-02 功能包](P1-02-ingest.md)。

## 范围：接口与迁移

`POST /ingest/batches/{id}/issues/{issueId}/resolve`（medium，可撤销）、`POST /ingest/batches/{id}/issues/{issueId}/escalate`（medium）。 迁移 `0040_ing_<功能>.py`。

## 依赖

P1-02-core。

## 必须复用的共用函数

见 [rules.md](../rules.md) 第 3 节。本功能重点：`PermissionService.store_scope` + `apply_store_scope`（店铺范围）、`make_action_dispatcher`（写动作）、`api_endpoint(..., idempotency="dispatcher")`（写接口幂等归属）、`ApprovalGateway.submit` → `ApprovalSubmission`（高风险）、`AuditRecorder`（工厂注入）、dispatcher 撤销登记（中风险）。 文件统一用 FileObject；投射写 EntityVersion（来源批次、原件行号、规则版本、操作者、被代表人）。

## 验收标准（逐条可测试）

1. resolve 支持补映射、判定重复、忽略并写原因；涉及钱和账的结论降为人工确认，AI 不能直接定。
2. escalate 转交上传该批数据的人，附 AI 尝试记录、证据和建议，并生成站内通知或待办（通知模块未有时写转交记录并提供查询）。
3. 有权调用返回 200，列表真正分页切片，`q`/`sort` 按草案实现。
4. 无权限点返回 404（不是 403），不存在的 id 返回 404，未登录返回统一 401 错误体。
5. 店铺/数据范围：列表只返回范围内数据（用 `store_scope` + `apply_store_scope`），范围外单条 404；空范围返回空列表。
6. 金额字段为 `Money{amountMinor,currency}` 万分位整数，无浮点；字段权限按 `PermissionService.serialize`。
7. 写动作经 `make_action_dispatcher(session, permission_service)` 在请求事务里派发；`api_endpoint` 声明 entity/action/permission/riskTier/idempotency 与 OpenAPI 草案一致。
8. 范围外写返回 403 `DATA_SCOPE_DENIED`；无权 404；未登录 401。
9. AI 按风险档：medium 直接执行并写 `agent_undo` 撤销记录（且有一条"撤销成功"测试）；high 只生成审批，审批前业务数据不变；critical AI 拒绝。人发起 high 按 ApprovalSubmission 的 `required/auto_effective/awaiting_initiator` 处理，不能自批。
10. 幂等：同人同键同体回放原响应；同键不同体 409；他人同键不可见（无权 404）；未登录同键 401 不回放；权限收回后回放 404。
11. `expectedVersion` 冲突返回 409，不覆盖。
12. 审计记录含 `actor_type`、`on_behalf_of`、`request_id`；AI 发起时含 agent 字段。
13. 请求结束后用全新 Session 能查到写入结果（真实提交）。
14. `check_merge_guard.py --base <切出点>` 0 命中，或命中已在验收报告中逐条豁免。
15. 独立验收报告 `<块>-accept.txt` 结论为"通过"，横向对比无不一致项。
16. rules.md 第 5 节全部检查 0 失败（SQLite 全量、MySQL `-m db`、双库迁移往返、ruff、mypy、文档链接、授权覆盖、API contract、密钥扫描）。

## 进度

已合回 `498058c`。工作树已拆。

## 待定 / 需拍板

无。
