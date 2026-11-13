# 审计、审批中心与实体动作执行器（P0-03-audit-approval-ontology 功能包）

- **旧任务卡：** [backend-phases.md P0-03](../_archive/backend-phases.md)（已归档）；仓库外：TASK-be-p0-audit、-audit-fix、-audit-fix2、-audit-nodef、TASK-be-p0-onto、-onto-fix、-onto-nodef、TASK-sec-fix3、TASK-sec-idem、TASK-merge-inc-b、TASK-merge-p0-tail
- **状态：** 已合入 main（撤销 `a83896e`）
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

让所有实体动作走统一执行器、版本记录和审批解析，并保留哈希链审计；中风险动作 24 小时可撤销，是 AI 直接执行中风险动作的前提。

## 范围

`audit`、`approvals`、`ontology`、`action-dispatcher`；路径前缀 `/audit`、`/approvals`、`/workflow/rules/resolve`、`/ontology/entity-types`、`/entities/{type}/{id}/lineage`。08 第 5.3、5.16、5.23 节。迁移 0023/0024 及尾部迁移。

## 涉及实体

`AuditLog`、`Approval`、`EntityType`、`EntityVersion`、`WorkflowRule`、`ActionExecution`、`AgentUndo`、`AuditExport`。

## 权限与 AI 风险

查询审计、实体定义和审批状态为 `none`；`Approval.decide` 与 `Approval.initiator_confirm` 为 `critical`，仅真人，不能自批。改账动作按 OpenAPI 的 `high`/`critical`：AI 最多起草/待审。

## 依赖

P0-01、P0-02、现有哈希链。

## 功能拆分（每个功能一个文件、一个工作树）

- 审计扩展与审批中心 be-p0-audit（已合入 f432fe0 及修复 c99cc4c、d9272b5）
- 实体目录、ActionDispatcher、EntityVersion be-p0-onto（已合入 c958d5d、ff2ed59）
- dispatcher 绑定请求事务 sec-fix3（已合入 2a2c5df）
- 幂等按调用身份隔离 sec-idem（已合入 2c36c46、64b824b）；ApprovalSubmission 统一（e96a470、f2c65c9、178d23b）
- [P0-03-audit-export](P0-03-audit-export.md) 审计导出包落库（已合入 6f68c2a）
- [P0-03-undo](P0-03-undo.md) 中风险动作撤销与每日摘要（已合入）

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/guard tests/integration -k "audit or approval or action" -q` 通过。
2. 并发审批只成功一次；不能自批；审计哈希可离线校验。
3. 幂等回放在身份/权限/范围/版本校验之后，按调用身份+方法+路由模板+请求体哈希隔离。
4. 写接口全部经 `make_action_dispatcher` 构造；仓库内无全局共享执行器、无审批结果兼容壳。
5. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
6. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
7. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
8. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
9. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
10. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

P0 已于 2026-11-12 15:32 放行（`p0tail-ok`）。审计导出 `6f68c2a`、撤销 `3cc3037`、新建类撤销 `a83896e` 均已合入。`data.db` 仍是当天 15:25 重建的那份。

## 待定 / 需拍板

等待发起人确认的超时时长为演示默认值，真实使用前需核实。
