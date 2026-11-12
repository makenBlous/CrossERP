# IM 审批与全量回归（P5-03-im-approval-regression 功能包）

- **旧任务卡：** [backend-phases.md P5-03](../_archive/backend-phases.md)（已归档）；仓库外无
- **状态：** 未开工
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

在平台内审批稳定后，以可插拔渠道接入 IM 卡片审批，并完成 237 个页面的全量回归。

## 范围

`channels` 的 `ApprovalChannel`；路径前缀 `/im/bindings`、`/im/approvals`、`/im/settings`、`/approvals`。IM 只产出决定命令，最终仍调用平台内 `approvals.decide`。 依据 08 v4 第 5.17 节（notify 的 IM 部分）、第 5.16 节、第 4.11 节。

## 涉及实体

`ApprovalChannel`、`ImBinding`、`Approval`、`DecisionCommand`、`SecurityEvent`。

## 权限与 AI 风险

IM 绑定、解绑、授权回调和审批设置保存 `critical`，仅真人；审批设置读取和卡片预览 `none`；IM 回调 `critical`，AI 不绕过平台内审批。

## 依赖

P0–P5 其他包、平台内审批、渠道适配器。

## 功能拆分（每个功能一个文件、一个工作树）

**待定。** 开工前从当时的 main 出发，按 08 第 5 节对应小节的接口表逐行拆成单功能文件（一个功能或一组必须耦合开发的功能一个文件、一个工作树），并在本节列出。下面只是按 08 小节划分的拆分方向，不是定稿：

- IM 渠道适配器与回调校验
- 全量回归（237 页）

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/web tests/guard tests/integration -k "approval or im or security" -q` 通过。
2. 重复回调只处理一次；回调签名校验失败记安全事件。
3. 记录累计页面数 237。
4. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
5. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
6. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
7. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
8. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
9. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

未开工。

## 待定 / 需拍板

首个 IM 渠道（飞书或企业微信，08 第 12.2 节第 9 条）未定；演示默认只验平台内审批。
