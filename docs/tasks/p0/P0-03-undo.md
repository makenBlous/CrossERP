# 中风险动作撤销与每日摘要（P0-03-undo）

- **旧任务卡：** TASK-p0-undo、TASK-p0-undo-nodef、TASK-merge-p0-tail（仓库外）
- **状态：** 合入中：3cc3037 已合入；75a0a01 审查不通过（把"中风险缺实体 ID 报错"放松成静默不登记），1dd2b8d 已用新提交恢复，merge-p0-tail 收尾中
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

08 v4：中风险动作允许 AI 直接执行的前提是 24 小时内可撤销；所有自动执行的低/中风险动作进每日站内摘要，每条可一键撤销。

## 范围：接口与迁移

`agent_undo` 表（id、suggestion_id 可空、undo_payload_json、deadline_at、undone_by、undone_at，必要时加 action_audit_id/entity_version 引用）；dispatcher 在 medium 成功后同事务写撤销记录；动作可声明撤销函数，否则按 EntityVersion 回退；撤销接口 `POST /agent/suggestions/{id}/undo`；每日摘要只读接口（路径以草案为准）。

## 依赖

P0-03 执行器、P1-01 catalog（接入撤销）。

## 必须复用的共用函数

`ActionDispatcher.undo`、`UndoPayload`、`crosserp.catalog.undo_restore`；撤销本身也走 dispatcher（权限、幂等、审计）。

## 验收标准（逐条可测试）

1. medium 动作执行后有撤销记录；中风险动作缺实体 ID 必须报错（不得静默不登记、照常执行）。
2. 只有原动作发起人、被代表人或有对应管理权限的人可以撤销，其他人 404。
3. 超过 24 小时返回 `UNDO_EXPIRED`；已撤销再撤销返回 409 `UNDO_ALREADY_APPLIED`；实体已被后续修改返回 409 版本冲突，不覆盖。
4. 不支持撤销的实体类型显式报错，不得记成撤销成功。
5. 品牌、类目等全局实体（不属于具体店铺）的撤销不被店铺范围误拦。
6. 中风险不设次数限额。
7. 撤销写审计，覆盖人和 AI；high 动作不产生撤销记录；critical 动作不可执行。
8. catalog 每个 medium 动作至少一条"撤销成功"测试。
9. 每日摘要列出"AI 今天替你做了 N 件事"，不推送、不弹窗。
10. 写动作经 `make_action_dispatcher(session, permission_service)` 在请求事务里派发；`api_endpoint` 声明 entity/action/permission/riskTier/idempotency 与 OpenAPI 草案一致。
11. 范围外写返回 403 `DATA_SCOPE_DENIED`；无权 404；未登录 401。
12. AI 按风险档：medium 直接执行并写 `agent_undo` 撤销记录（且有一条"撤销成功"测试）；high 只生成审批，审批前业务数据不变；critical AI 拒绝。人发起 high 按 ApprovalSubmission 的 `required/auto_effective/awaiting_initiator` 处理，不能自批。
13. 幂等：同人同键同体回放原响应；同键不同体 409；他人同键不可见（无权 404）；未登录同键 401 不回放；权限收回后回放 404。
14. `expectedVersion` 冲突返回 409，不覆盖。
15. 审计记录含 `actor_type`、`on_behalf_of`、`request_id`；AI 发起时含 agent 字段。
16. 请求结束后用全新 Session 能查到写入结果（真实提交）。
17. `check_merge_guard.py --base <切出点>` 0 命中，或命中已在验收报告中逐条豁免。
18. 独立验收报告 `<块>-accept.txt` 结论为"通过"，横向对比无不一致项。
19. rules.md 第 5 节全部检查 0 失败（SQLite 全量、MySQL `-m db`、双库迁移往返、ruff、mypy、文档链接、授权覆盖、API contract、密钥扫描）。

## 进度

3cc3037 合入（11-12 14:18）、fc4192b、d3b7c4c、75a0a01。75a0a01 审查不通过；1dd2b8d 恢复报错与原断言并删除静默兜底，2e50459、71a60d9 跟进。之后：撤销接入 catalog → 删最后一处兜底 → 全量 → 重建 data.db → 写 p0tail-ok。

## 待定 / 需拍板

AI 能否撤销按草案中该接口的风险档处理。
