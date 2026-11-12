# 认证、会话与平台底座（P0-01-platform 功能包）

- **旧任务卡：** [backend-phases.md P0-01](../_archive/backend-phases.md)（已归档）；仓库外：TASK-be-p0-base、TASK-be-p0-platform、TASK-be-p0-platform-nodef、TASK-pf-auth/account/files/jobs/stores/docs、TASK-mysql、TASK-merge-p0、TASK-merge-inc-a
- **状态：** 已合入 main
- **设计依据：** [08 v4](../../design/08-后端模块与API设计.md) 第 8.1 节分期；[实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)
- **规则：** [rules.md](../rules.md)；验收流程 [acceptance.md](../acceptance.md)

## 方向与业务价值

让前端通过统一会话、文件、任务、店铺和错误码接口接入真实后端；是其他所有模块的地基（api 骨架、错误码、幂等、Principal、PermissionService/AuditRecorder/ApprovalGateway/ActionDispatcher 接口、契约守卫）。

## 范围

OpenAPI `auth`、`platform`、`files`、`tasks`、`stores`、幂等与错误响应；路径前缀 `/auth`、`/files`、`/tasks`、`/stores`、`/health`。`GET /auth/me` 是会话和有效权限的唯一来源。08 第 5.1 节（22 个接口）。迁移 0020/0021（合并时已线性化）。

## 涉及实体

`UserAccount`、`ApiToken`、`FileObject`、`Task`、`Store`、`IdempotencyKey`、`DocumentLink`。

## 权限与 AI 风险

登录、当前用户和文件元数据读取为 `none`；文件上传 `low`；店铺新建/修改仅真人（`system:write`）。登录、登出、重置密码等认证动作 AI 禁用。AI 继承登录人权限，不能扩权。

## 依赖

数据库会话、现有登录实现、OpenAPI 草案、MySQL 测试实例（infra-mysql）。

## 功能拆分（每个功能一个文件、一个工作树）

- [P0-01-auth](P0-01-auth.md) 登录、登出、当前用户、忘记/重置密码
- [P0-01-account](P0-01-account.md) 我的账户：资料、改密码、API Token、我的会话
- [P0-01-files](P0-01-files.md) 文件对象
- [P0-01-jobs](P0-01-jobs.md) 后台任务与自调度 worker
- [P0-01-stores](P0-01-stores.md) 店铺与数据范围
- [P0-01-docs](P0-01-docs.md) 单据关联

## 包级验收标准（全部功能合入后逐条验证）

1. 未登录统一 401；重复幂等键不重复写入；权限矩阵覆盖登录人、停用账号和数据范围。
2. `uv run pytest tests/web tests/integration -q` 通过。
3. 包内每个功能文件的验收标准全部通过，且各自的独立验收报告结论为"通过"。
4. 同一动作三路径一致：网页、主/子智能体（带委托通行证）、导入投射的成功结果、拒绝原因和审计字段一致（08 第 8.1 节）。
5. 21 角色 × AI 开/关 的真实接口回归通过（08 第 8.1 节）。
6. 迁移往返：MySQL 8.4 与 SQLite 都 `upgrade head → downgrade base → upgrade head`，单一 head。
7. 不删除已有测试；安全断言无放松（check_merge_guard 对包内全部合并提交 0 未豁免命中）。
8. mock 点击与 OpenAPI 契约一致；前端默认 mock 模式回归不变；密钥扫描无命中。

## 进度

base+platform 合并 d0bea5c（11-12 01:38）；pf-jobs 285f7af、pf-stores 75a2971–d07372a、pf-files 24ca557–58b54d0、pf-auth b84385e–26ef0a5、pf-account 3fd08b9–2fd57d3、pf-docs a8ff7c2–fefe4a5；之后 sec-idem（2c36c46、64b824b）把登录、忘记/重置密码声明为不参与幂等回放。

## 待定 / 需拍板

账号与店铺清单未定，演示默认单法人、内网服务器（真实使用前需核实）。
