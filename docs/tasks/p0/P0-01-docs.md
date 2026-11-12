# 单据关联（P0-01-docs）

- **旧任务卡：** TASK-pf-docs（仓库外）
- **状态：** 已合入 main（a8ff7c2–fefe4a5；范围统一 3a7b56d）
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

把订单、采购、结算等单据串成可追溯的链。

## 范围：接口与迁移

DocumentLink 查询接口；`src/crosserp/api/routers/documents.py`。

## 依赖

P0-01 底座、P0-02 IAM。

## 必须复用的共用函数

`PermissionService.store_scope`/`data_scope_filter`（不得按 `principal.data_scope` 会话快照过滤）。

## 验收标准（逐条可测试）

1. 关联查询按调用人权限过滤：看不到无权单据，链上无权节点不泄露。
2. 链查询深度/环路按 08 定义处理（环路显式报错或去重）；分页格式统一。
3. 有权调用返回 200，列表真正分页切片，`q`/`sort` 按草案实现。
4. 无权限点返回 404（不是 403），不存在的 id 返回 404，未登录返回统一 401 错误体。
5. 店铺/数据范围：列表只返回范围内数据（用 `store_scope` + `apply_store_scope`），范围外单条 404；空范围返回空列表。
6. 金额字段为 `Money{amountMinor,currency}` 万分位整数，无浮点；字段权限按 `PermissionService.serialize`。
7. `check_merge_guard.py --base <切出点>` 0 命中，或命中已在验收报告中逐条豁免。
8. 独立验收报告 `<块>-accept.txt` 结论为"通过"，横向对比无不一致项。
9. rules.md 第 5 节全部检查 0 失败（SQLite 全量、MySQL `-m db`、双库迁移往返、ruff、mypy、文档链接、授权覆盖、API contract、密钥扫描）。

## 进度

已合入。

## 待定 / 需拍板

无。
