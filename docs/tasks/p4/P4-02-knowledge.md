# 知识库与规则编译（P4-02-knowledge 功能包）

- **旧任务卡：** [backend-phases.md P4-02](../_archive/backend-phases.md)（已归档）；仓库外无
- **状态：** 未开工
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

对业务知识、规则和实体页做权限隔离的整理、检索、体检和引用。

## 范围

`knowledge`；路径前缀 `/kb/spaces`、`/kb/pages`、`/kb/compile-runs`、`/kb/search`、`/kb/entity-pages`。 依据 08 v4 第 5.20 节（kb，35 个）、第 9.6 节。

## 涉及实体

`KnowledgeSpace`、`KnowledgePage`、`KnowledgeCompileRun`、`KnowledgeReview`、`EntityType`。

## 权限与 AI 风险

读取继承来源空间和实体权限 `none`；知识页和版本草稿 `medium`；提交 `high`；归档、空间 ACL/成员和审核决定 `critical`；编译、索引和体检 `low`。

## 依赖

P0-02、P4-01、P1-02 溯源。

## 功能拆分（每个功能一个文件、一个工作树）

**待定。** 开工前从当时的 main 出发，按 08 第 5 节对应小节的接口表逐行拆成单功能文件（一个功能或一组必须耦合开发的功能一个文件、一个工作树），并在本节列出。下面只是按 08 小节划分的拆分方向，不是定稿：

- 空间与 ACL
- 知识页与版本、审核
- 编译、索引与检索

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/web tests/agent -k "knowledge or kb" -q` 通过。
2. 无权限来源不可检索，不跨空间泄露；网页与 Agent 返回同一过滤结果。
3. 空间配置审核人就必须审核；未配置时直接生效并留痕。
4. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
5. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
6. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
7. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
8. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
9. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

未开工。

## 待定 / 需拍板

向量检索实现与保留期未定，演示默认使用现有数据库查询，真实使用前需核实。
