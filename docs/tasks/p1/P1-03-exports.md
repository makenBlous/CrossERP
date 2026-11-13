# 导出产物列表（P1-03-exports）

- **旧任务卡：** TASK-p1-fin-exports（仓库外）
- **状态：** 已合入 main（`d3a6926`，合回 `050e9f5`）
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

结算对账快赢的一部分，见 [P1-03 功能包](P1-03-finance.md)。

## 范围：接口与迁移

`GET /finance/exports`（ExportPackage.list，report:read，none）：列出导出产物元数据与 SHA-256，不提供下载（下载走 `GET /files/{id}`）。 路由 `src/crosserp/api/routers/fin_<功能>.py`。

## 依赖

P0、P0-01-files。

## 必须复用的共用函数

见 [rules.md](../rules.md) 第 3 节。本功能重点：`PermissionService.store_scope` + `apply_store_scope`（店铺范围）、`make_action_dispatcher`（写动作）、`api_endpoint(..., idempotency="dispatcher")`（写接口幂等归属）、`ApprovalGateway.submit` → `ApprovalSubmission`（高风险）、`AuditRecorder`（工厂注入）、dispatcher 撤销登记（中风险）。 复用已有计算：`crosserp.recon`、`profit`、`issues`、`ledger`、`vouchers`、`db/repo/{recon,profit,fx,issues}.py`；账务只经 `ledger/write_service.py` 写草稿。**不得改共享组件**（dispatcher、middleware、permissions、principal、_platform_common）。

## 验收标准（逐条可测试）

1. 按数据范围过滤；filters 缺 storeIds/legalEntities 时不得放行（原实现失败放行，需改）。
2. `ledger/write_service.py` 不新增可选 `output_dir`，文件目录只有一个定义。
3. 有权调用返回 200，列表真正分页切片，`q`/`sort` 按草案实现。
4. 无权限点返回 404（不是 403），不存在的 id 返回 404，未登录返回统一 401 错误体。
5. 店铺/数据范围：列表只返回范围内数据（用 `store_scope` + `apply_store_scope`），范围外单条 404；空范围返回空列表。
6. 金额字段为 `Money{amountMinor,currency}` 万分位整数，无浮点；字段权限按 `PermissionService.serialize`。
7. `check_merge_guard.py --base <切出点>` 0 命中，或命中已在验收报告中逐条豁免。
8. 独立验收报告 `<块>-accept.txt` 结论为"通过"，横向对比无不一致项。
9. rules.md 第 5 节全部检查 0 失败（SQLite 全量、MySQL `-m db`、双库迁移往返、ruff、mypy、文档链接、授权覆盖、API contract、密钥扫描）。

## 进度

已合回 `050e9f5`。工作树已拆。

## 待定 / 需拍板

无。
