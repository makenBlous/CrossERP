# 数据进入、清洗、去重与投射（P1-02-ingest 功能包）

- **旧任务卡：** [backend-phases.md P1-02](../_archive/backend-phases.md)（已归档）；仓库外：P1-ING-COMMON、TASK-p1-ing-*（含 -nodef/-nodef2）、TASK-merge-p1-ing
- **状态：** 5 个功能已开发、待合并（ing-ok 已写；merge-p1-ing 由 chain6 在 p0tail-ok 后自动启动）
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

原件不可改，经过清洗校验、去重和实体对齐后，投射为预定义实体动作；所有导入入口统一到这条链路（08 第 9.3 节：落地 → 清洗 → 去重 → 投射 → 溯源）。

## 范围

`ingest`；路径前缀 `/ingest/batches`、`/ingest/raw-records`、`/ingest/issues`、`/ingest/mapping-rules`、`/ingest/dedup-candidates`、`/entities/{type}/{id}/lineage`。08 第 5.24 节（12 个接口）。迁移 `0040_ing_*`，现有 import_batch/raw_row 直接升级改造，不做双轨。

## 涉及实体

`IngestBatch`、`FileObject`、`RawRecord`、`CleansingIssue`、`MappingRule`、`DedupCandidate`、`EntityVersion`。

## 权限与 AI 风险

原件和问题读取 `none`；问题处理、去重合并、投射为 `medium`；映射规则修改 `high`；批次替代 `critical`。AI 先处理清洗问题，处理不了转交上传这批数据的人；钱账只生成草稿。

## 依赖

P0-01-files、P0-03。

## 功能拆分（每个功能一个文件、一个工作树）

- [P1-02-core](P1-02-core.md)
- [P1-02-dedup](P1-02-dedup.md)
- [P1-02-issue](P1-02-issue.md)
- [P1-02-project](P1-02-project.md)
- [P1-02-rules](P1-02-rules.md)

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/integration tests/guard -k "ingest or import or lineage" -q` 通过。
2. 同一文件重放不重复投射；坏行有原因码且原件保留。
3. 投射以导入发起人（AI 发起时以被代表人）身份对每个目标动作重新校验权限。
4. 共享组件（`api/__init__.py`、dispatcher、gateway、permissions）上的分支改动全部丢弃，以 main 的 sec-scope/sec-idem/ApprovalSubmission 为准。
5. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
6. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
7. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
8. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
9. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
10. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

core f00580a、dedup f976cf0、issue 7ea9dfa、project d1631e0、rules cc616fa（各自工作树，未合入）。合并任务 TASK-merge-p1-ing 已写好，等 p0tail-ok。

## 待定 / 需拍板

外部平台账号与同步频率未定，P1 只验文件导入（真实使用前需核实）。
