# 数据范围挂到角色、默认角色模板（P0-02-scope-roles）

- **旧任务卡：** TASK-sec-scope2.draft（仓库外草稿）
- **状态：** 已合入（2026-11-13，`86ac2ec`）
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

让店铺运营只看到自己负责的店铺、主管看所管店铺组、老板看全部；默认角色模板按设计配置，演示时各角色看到合理数据。

## 范围：接口与迁移

`IamDataScopeRule` 加 `role_id`（可全局，也可挂角色），需要迁移，SQLite/MySQL 都能往返；接入 08 的用户例外 `user_permission_override`、`user_store_grant`；新增范围类型（如 `ownedStores`）解析成该用户负责的店铺集合。默认模板按 02 第 13.2 节和 01 第 812 行起的表。演示数据只写种子脚本。

## 依赖

P0-02 已合入部分（`iam/scope.py`）、merge-p1-fin 完成。

## 必须复用的共用函数

只改 `crosserp.iam.scope` 与 IAM 服务；业务模块不改，继续只调 `PermissionService.store_scope`。

## 验收标准（逐条可测试）

1. `store_scope` = 用户所有有效角色（含继承链）规则的并集 → 再算用户例外 → 最后与 AI 收窄规则取交集。
2. 缺失或格式不对一律报错，不放行。
3. 不同角色看到的店铺不同；多个角色取并集；用户例外生效。
4. AI 收窄只能缩小、不能扩大。
5. 店铺运营只能看到自己负责的店铺；没有负责店铺的店铺运营什么都看不到；老板看到全部。
6. "本人负责的店铺"的来源先在 02/04/08 中确认（store 负责人字段或 `user_store_grant`），不自创字段。
7. `check_merge_guard.py --base <切出点>` 0 命中，或命中已在验收报告中逐条豁免。
8. 独立验收报告 `<块>-accept.txt` 结论为"通过"，横向对比无不一致项。
9. rules.md 第 5 节全部检查 0 失败（SQLite 全量、MySQL `-m db`、双库迁移往返、ruff、mypy、文档链接、授权覆盖、API contract、密钥扫描）。

## 进度

已合回 `86ac2ec`。功能提交 `f043f2f`，期间令牌修复 `01229df`。本次合回到此为止，没有重建 `data.db`。

## 待定 / 需拍板

店铺负责人字段来源需按 02/04/08 确认后再定。
