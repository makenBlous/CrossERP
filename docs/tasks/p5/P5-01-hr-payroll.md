# 人事与薪资（P5-01-hr-payroll 功能包）

- **旧任务卡：** [backend-phases.md P5-01](../_archive/backend-phases.md)（已归档）；仓库外无
- **状态：** 未开工
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

接入员工档案、组织、合同、考勤、薪资、社保公积金和工资条。

## 范围

`hr`、`payroll`；路径前缀 `/hr/employees`、`/hr/contracts`、`/hr/attendance`、`/payroll/runs`、`/payroll/slips`、`/payroll/rules`。 依据 08 v4 第 5.18 节（hr，24 个）。

## 涉及实体

`Employee`、`EmploymentContract`、`AttendanceRecord`、`PayrollRun`、`PayrollSlip`、`SocialSecurityRule`。

## 权限与 AI 风险

薪资查询按字段和本人范围 `none`；请假 `medium`；薪资计算、发布、导出及员工/部门维护 `critical`，仅真人并必须审批。

## 依赖

P0 权限/审计、P3 财务写出口。

## 功能拆分（每个功能一个文件、一个工作树）

**待定。** 开工前从当时的 main 出发，按 08 第 5 节对应小节的接口表逐行拆成单功能文件（一个功能或一组必须耦合开发的功能一个文件、一个工作树），并在本节列出。下面只是按 08 小节划分的拆分方向，不是定稿：

- 员工、组织与合同
- 考勤与请假
- 薪资批次、工资条与社保公积金

## 包级验收标准（全部功能合入后逐条验证）

1. `uv run pytest tests/web tests/guard -k "employee or payroll or salary" -q` 通过。
2. 越权字段返回 403 或脱敏；薪资发布无审批失败。
3. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
4. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
5. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
6. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
7. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
8. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

未开工。

## 待定 / 需拍板

薪资和个税口径为演示默认值，真实使用前需核实。前端模块注册表里人事默认关闭。
