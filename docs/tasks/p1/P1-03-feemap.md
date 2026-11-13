# 费用映射与列映射（P1-03-feemap）

- **旧任务卡：** 无（进度文件中记为 fin-feemap，尚无任务卡）
- **状态：** 已合入 main（`3891276`）
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

结算对账快赢的一部分，见 [P1-03 功能包](P1-03-finance.md)。

## 范围：接口与迁移

`/finance/fee-map`、`/finance/column-maps` 的剩余接口（column-maps 的 PUT 已在 P1-02-rules 统一为 MappingRule）；MappingRule.confirm 验证接口（integration:write，high，自主决策 34）。 路由 `src/crosserp/api/routers/fin_<功能>.py`。

## 依赖

P1-02-rules 合入 main。

## 必须复用的共用函数

见 [rules.md](../rules.md) 第 3 节。本功能重点：`PermissionService.store_scope` + `apply_store_scope`（店铺范围）、`make_action_dispatcher`（写动作）、`api_endpoint(..., idempotency="dispatcher")`（写接口幂等归属）、`ApprovalGateway.submit` → `ApprovalSubmission`（高风险）、`AuditRecorder`（工厂注入）、dispatcher 撤销登记（中风险）。 复用已有计算：`crosserp.recon`、`profit`、`issues`、`ledger`、`vouchers`、`db/repo/{recon,profit,fx,issues}.py`；账务只经 `ledger/write_service.py` 写草稿。**不得改共享组件**（dispatcher、middleware、permissions、principal、_platform_common）。

## 验收标准（逐条可测试）

1. 所有映射统一为 MappingRule 版本，不保留旧的 fee-map 存储。
2. MappingRule.confirm 为 high：AI 只生成审批。
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

已合回 `3891276`。只补了 `POST /finance/fee-map/{id}/confirm`。已有列表和列映射保存没有重写。

## 待定 / 需拍板

接口清单以 08 第 5.10 节为准，开工前补齐。
