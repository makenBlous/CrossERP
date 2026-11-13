# 商品主数据与映射（P1-01-catalog 功能包）

- **旧任务卡：** [backend-phases.md P1-01](../_archive/backend-phases.md)（已归档）；仓库外：P1-COMMON、TASK-p1-cat-*（含 -nodef）、TASK-merge-p1-cat、TASK-merge-p1-cat-finish
- **状态：** 已合入 main（撤销接入 `a83896e`）
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

先接入见效最快的 SKU、Listing、类目、品牌、组合装和平台映射页面，是订单、库存、财务的主数据基础。

## 范围

`catalog`；路径前缀 `/catalog/skus`、`/catalog/costs`、`/catalog/listings`、`/catalog/categories`、`/catalog/brands`、`/catalog/mappings`、`/catalog/bundles`、`/catalog/lookups`。08 第 5.5 节（28 个接口）。迁移 `0030_cat_*`（已线性化）。

## 涉及实体

`Sku`、`SkuCost`、`Listing`、`Category`、`Brand`、`SkuMapping`、`Bundle`、`CatalogLookup`。

## 权限与 AI 风险

查询 `none`；普通新增/修改 `medium`（可撤销、进每日摘要）；`/catalog/costs` 新增和 `/catalog/mappings/confirm` 为 `high`；`/catalog/bundles/deactivate` 为 `critical`。删除用作废，不物理删除；AI 建议映射必须人确认。

## 依赖

P0 全部。

## 功能拆分（每个功能一个文件、一个工作树）

- [P1-01-category](P1-01-category.md)
- [P1-01-brand](P1-01-brand.md)
- [P1-01-sku](P1-01-sku.md)
- [P1-01-listing](P1-01-listing.md)
- [P1-01-mapping](P1-01-mapping.md)
- [P1-01-bundle](P1-01-bundle.md)
- [P1-01-cost](P1-01-cost.md)

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/web tests/integration -k "catalog or sku or listing" -q` 通过。
2. 金额以 Money 返回；网页/Agent/导入三路径的成功和拒绝一致。
3. 所有 catalog 路由的店铺范围都走 `store_scope` + `apply_store_scope`（无自写 `_store_ids`）。
4. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
5. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
6. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
7. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
8. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
9. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

7 个功能全部合入（category `0e971cf` 至 cost `868a5f3`）；收尾 `cbb6b5c`；幂等跳过范围收窄 `1f62e85`；店铺范围改走 IAM `c4164bb`。撤销接入已随 `a83896e` 合入。

## 待定 / 需拍板

SKU 成本会计口径使用演示默认值，真实使用前需核实。
