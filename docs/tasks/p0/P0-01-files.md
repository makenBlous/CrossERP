# 文件对象（P0-01-files）

- **旧任务卡：** TASK-pf-files（仓库外）
- **状态：** 已合入 main（24ca557–58b54d0，multipart 幂等哈希 8ba58ee）
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

所有上传、导出产物统一走 FileObject，记录 SHA-256 和上传人。

## 范围：接口与迁移

`/files` 上传（`low`）与元数据读取；`src/crosserp/api/routers/files.py`。

## 依赖

P0-01 底座。

## 必须复用的共用函数

FileObject 存储目录只有一个定义；`api_endpoint`（上传的幂等归属按 main 的声明）。

## 验收标准（逐条可测试）

1. 上传按 SHA-256 去重：同文件二次上传返回同一对象，不重复落盘；记录上传人。
2. 存储目录可配，测试用临时目录；元数据读取不回传存储路径等内部信息。
3. 超大或空文件的错误码按草案；重复 Idempotency-Key 不重复写。
4. 有权调用返回 200，列表真正分页切片，`q`/`sort` 按草案实现。
5. 无权限点返回 404（不是 403），不存在的 id 返回 404，未登录返回统一 401 错误体。
6. 店铺/数据范围：列表只返回范围内数据（用 `store_scope` + `apply_store_scope`），范围外单条 404；空范围返回空列表。
7. 金额字段为 `Money{amountMinor,currency}` 万分位整数，无浮点；字段权限按 `PermissionService.serialize`。
8. 写动作经 `make_action_dispatcher(session, permission_service)` 在请求事务里派发；`api_endpoint` 声明 entity/action/permission/riskTier/idempotency 与 OpenAPI 草案一致。
9. 范围外写返回 403 `DATA_SCOPE_DENIED`；无权 404；未登录 401。
10. AI 按风险档：medium 直接执行并写 `agent_undo` 撤销记录（且有一条"撤销成功"测试）；high 只生成审批，审批前业务数据不变；critical AI 拒绝。人发起 high 按 ApprovalSubmission 的 `required/auto_effective/awaiting_initiator` 处理，不能自批。
11. 幂等：同人同键同体回放原响应；同键不同体 409；他人同键不可见（无权 404）；未登录同键 401 不回放；权限收回后回放 404。
12. `expectedVersion` 冲突返回 409，不覆盖。
13. 审计记录含 `actor_type`、`on_behalf_of`、`request_id`；AI 发起时含 agent 字段。
14. 请求结束后用全新 Session 能查到写入结果（真实提交）。
15. `check_merge_guard.py --base <切出点>` 0 命中，或命中已在验收报告中逐条豁免。
16. 独立验收报告 `<块>-accept.txt` 结论为"通过"，横向对比无不一致项。
17. rules.md 第 5 节全部检查 0 失败（SQLite 全量、MySQL `-m db`、双库迁移往返、ruff、mypy、文档链接、授权覆盖、API contract、密钥扫描）。

## 进度

已合入。

## 待定 / 需拍板

无。
