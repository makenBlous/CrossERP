# 权限引擎与旧 15 点映射（P0-02-iam 功能包）

- **旧任务卡：** [backend-phases.md P0-02](../_archive/backend-phases.md)（已归档）；仓库外：TASK-be-p0-iam、TASK-be-p0-iam-fix、TASK-be-p0-iam-nodef、TASK-sec-fix2、TASK-sec-scope、TASK-sec-scope2.draft
- **状态：** 主体已合入 main；店铺范围挂到角色（P0-02-scope-roles）未开工
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

把旧后端 15 个权限点映射到前端 811 个 `doctype:action` 目录，消除权限漂移；所有权限、数据范围、字段权限只有 IAM 一个来源。

## 范围

`iam` 模块的角色继承、用户例外、数据范围、字段策略、职责分离、临时授权和权限解释；路径前缀 `/admin/roles`、`/admin/permissions`、`/admin/permission-matrix`、`/admin/data-scopes`、`/admin/field-policies`。08 第 5.2 节（35 个接口）。迁移 0022/0023（种子角色）。

## 涉及实体

`Role`、`PermissionPoint`、`DataScope`、`FieldPolicy`、`TempGrant`、`AccessReview`、`SodRule`。

## 权限与 AI 风险

查询权限目录为 `none`；改角色、字段和数据范围为 `critical`，仅真人并按审批规则；AI 不可调用权限类动作。

## 依赖

P0-01、前端 `permissionCatalog`、OpenAPI 草案。

## 功能拆分（每个功能一个文件、一个工作树）

- IAM 权限引擎与 15 点映射（已合入，无单独功能文件：be-p0-iam 系列卡）
- 统一权限来源 sec-fix2（已合入 4592a1a、3803221b）
- 统一店铺范围与成本字段 sec-scope（已合入 3a7b56d、c4164bb）
- [P0-02-scope-roles](P0-02-scope-roles.md) 数据范围挂到角色、默认角色模板（未开工）

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/guard tests/web -k "permission or route" -q` 通过。
2. 21 角色 × AI 开/关矩阵逐项返回预期状态码；同一动作经网页、Agent 和导入投射的拒绝原因一致。
3. 业务代码里没有按会话快照或角色名的授权判断（全仓 grep 证据）。
4. 店铺范围缺规则、格式错、未知范围类型都报 `VALIDATION_FAILED`，不放行；空集生成恒假条件。
5. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
6. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
7. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
8. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
9. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
10. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

IAM 合并 438d5bd–9938aff（11-12 04:27–04:40）；sec-fix2 4592a1a、3803221b；sec-scope 3a7b56d + c4164bb（catalog 改走 IAM 唯一函数）。sec-scope2 草稿已写，计划在 merge-p1-fin 之后开工，开工后需要再重建一次 data.db（已授权，旧库改名备份）。

## 待定 / 需拍板

811 点的 manifest 源头待定（08 第 12.2 节第 6 条），演示默认由模块 manifest 注册，真实使用前需核实。
