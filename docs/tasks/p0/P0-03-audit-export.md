# 审计导出包落库（P0-03-audit-export）

- **旧任务卡：** TASK-p0-audit-export、TASK-p0-audit-export-nodef（仓库外）
- **状态：** 已合入 main（6f68c2a）
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

审计导出包要落库、可校验、可追溯，不能只放在内存或临时目录。

## 范围：接口与迁移

OpenAPI audit 导出相关接口；文件走 FileObject（SHA-256）；元数据写 `audit_export`/`export_artifact`（发起人、actor_type、on_behalf_of、筛选条件、记录范围、链头哈希、文件哈希、创建时间、状态），表结构不够就改表加迁移。

## 依赖

P0-03 审计、P0-01-files。

## 必须复用的共用函数

FileObject（唯一文件目录定义）、`AuditRecorder`、`make_action_dispatcher`。

## 验收标准（逐条可测试）

1. 落库字段完整；重复请求幂等。
2. 下载按审计导出权限点校验，无权 404；每次下载都记审计（敏感读也记）。
3. 下载时校验 SHA-256，与落库值不一致返回明确错误码并记安全事件（篡改测试）。
4. 重启（新建 engine）后仍可列出和下载。
5. AI 按该接口在草案中的风险档处理，不自行改档。
6. 有权调用返回 200，列表真正分页切片，`q`/`sort` 按草案实现。
7. 无权限点返回 404（不是 403），不存在的 id 返回 404，未登录返回统一 401 错误体。
8. 店铺/数据范围：列表只返回范围内数据（用 `store_scope` + `apply_store_scope`），范围外单条 404；空范围返回空列表。
9. 金额字段为 `Money{amountMinor,currency}` 万分位整数，无浮点；字段权限按 `PermissionService.serialize`。
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

已合入 6f68c2a；原全局共享执行器已删除。

## 待定 / 需拍板

无。
