# 导入批次核心：落地、清洗、映射规则版本、只读接口（P1-02-core）

- **旧任务卡：** TASK-p1-ing-core、-nodef（仓库外）
- **状态：** 已合入 main（`f00580a`，合回 `498058c`）
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

数据进入链路的一部分，见 [P1-02 功能包](P1-02-ingest.md)。

## 范围：接口与迁移

表与模型：IngestBatch 状态机（uploaded→landed→cleansed→projected，landed/cleansed→failed 可重试，projected→superseded）、RawRecord（不可变）、CleansingIssue、MappingRule（带版本）。接口：`GET /ingest/batches`、`GET /ingest/batches/{id}`（各阶段计数）、`GET /ingest/batches/{id}/raw-records`、`GET /ingest/batches/{id}/issues`、`GET /ingest/mapping-rules`。耦合理由：清洗必须按指定版本的规则解析，四张表同一链路一起落地。 迁移 `0040_ing_<功能>.py`。

## 依赖

P0-01-files、P0-03。

## 必须复用的共用函数

见 [rules.md](../rules.md) 第 3 节。本功能重点：`PermissionService.store_scope` + `apply_store_scope`（店铺范围）、`make_action_dispatcher`（写动作）、`api_endpoint(..., idempotency="dispatcher")`（写接口幂等归属）、`ApprovalGateway.submit` → `ApprovalSubmission`（高风险）、`AuditRecorder`（工厂注入）、dispatcher 撤销登记（中风险）。 文件统一用 FileObject；投射写 EntityVersion（来源批次、原件行号、规则版本、操作者、被代表人）。

## 验收标准（逐条可测试）

1. 从 FileObject 生成批次和原始记录，记录 SHA-256、来源、接收时间；同一原件重复上传返回已有批次。
2. 按 MappingRule 指定版本解析列；统一编码、日期、时区、币种、单位；校验必填、万分位金额精度、期间、借贷方向。
3. 问题行进隔离区并生成 CleansingIssue，其余行继续。
4. 原件不可修改、不删除（有测试）。
5. raw-records 敏感字段按字段权限脱敏，敏感读也记审计。
6. 现有各处导入入口改为调用这条链路，旧清洗逻辑删除。
7. 有权调用返回 200，列表真正分页切片，`q`/`sort` 按草案实现。
8. 无权限点返回 404（不是 403），不存在的 id 返回 404，未登录返回统一 401 错误体。
9. 店铺/数据范围：列表只返回范围内数据（用 `store_scope` + `apply_store_scope`），范围外单条 404；空范围返回空列表。
10. 金额字段为 `Money{amountMinor,currency}` 万分位整数，无浮点；字段权限按 `PermissionService.serialize`。
11. `check_merge_guard.py --base <切出点>` 0 命中，或命中已在验收报告中逐条豁免。
12. 独立验收报告 `<块>-accept.txt` 结论为"通过"，横向对比无不一致项。
13. rules.md 第 5 节全部检查 0 失败（SQLite 全量、MySQL `-m db`、双库迁移往返、ruff、mypy、文档链接、授权覆盖、API contract、密钥扫描）。

## 进度

已合回 `498058c`。工作树已拆。

## 待定 / 需拍板

无。
