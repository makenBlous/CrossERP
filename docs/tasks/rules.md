# 后端开发共用规则（所有功能任务必须遵守）

> 本文件合并了仓库外原有的 `COMMON.md`、`NODEF.md`、`DBISO.md`、`P1-COMMON.md`、`P1-ING-COMMON.md`、`P1-FIN-COMMON.md` 以及监督方历次追加的硬性规则（截至 2026-11-12）。之后新任务卡只引用本文件，不再引用仓库外的规则文件。
> 规则优先级见 [README](README.md) 的"规则优先级"一节。

## 1. 依据（先读，以这些为准）

- [`AGENTS.md`](../../AGENTS.md)、[`docs/dev/开发规则.md`](../dev/开发规则.md)、[`docs/dev/测试与回归.md`](../dev/测试与回归.md)、[`docs/backend/README.md`](../backend/README.md)。
- [08 后端模块与 API 设计 v4](../design/08-后端模块与API设计.md) 及附件 [实体目录](../design/08/ontology-entities.yaml)、[OpenAPI 草案](../design/08/openapi-draft.yaml)、[页面接口覆盖](../design/08/page-api-coverage.csv)；财务补齐看 [07 成本记账与补货计划补齐](../design/07-成本记账与补货计划补齐.md)。
- 本目录下你那块的功能文件（方向、依赖、验收标准）。
- 接口路径、权限点 `x-crosserp.permission`、风险档 `x-crosserp.riskTier`、实体/动作名一律以 OpenAPI 草案和实体目录为准，不得自行改档。

## 2. 已定决策（不得违背）

- Python 后端沿用 FastAPI + SQLAlchemy 2 + Alembic + Pydantic 2。正式库 MySQL 8.4，SQLite 只做演示和默认测试，PostgreSQL 仅备选；迁移只用通用类型。内网、单法人、不做多租户。
- 以本体实体为核心：接口 = 实体动作的投影。所有写动作走统一 ActionDispatcher，顺序固定：身份与数据范围 → 权限点 → 风险档 → 职责分离 → 幂等与版本 → 业务动作 → 实体版本 + 审计，同一事务。
- AI 继承登录人权限，只能收窄不能扩权；子智能体与主智能体执行权相同，每步按被代表人当前权限回查。
- 风险 5 档：`none`（只读，含钱和账的查询、对账计算）AI 可直接做；`low`/`medium` AI 可直接做，**中风险不设次数限额**，必须 24 小时内可撤销，进每日站内摘要；`high`（改账类）AI 最多到起草/待审；`critical` AI 禁用，仅真人。`Role.update`、`Approval.decide`、`Approval.initiator_confirm` 等是 `critical`。
- 审批：审批人从流程配置解析（ApproverResolver），排除提交人和被代表人。配了审批人且解析到可用账号就必须走审批（老板也一样），不能自批；没配或解析不到时，人发起的直接生效并留痕（原因码 `no_rule`/`no_account`/`only_self`）；AI 发起的高风险或钱账动作退回发起人本人确认（`awaiting_initiator`，`POST /approvals/{id}/initiator-confirm`，仅真人）。不设金额上限。
- 审计同时覆盖人和 AI：`actor_type`、`agent_id`、`on_behalf_of`、`delegation_id`、`run_id`、`tool_call_id`、`is_subagent`、`channel`、`request_id` 等；哈希链只追加。
- 金额 `Money = {amountMinor:int, currency}`，万分位整数，禁止浮点；汇率和高精度单价用十进制字符串。JSON 用 camelCase；错误体 `{code,message,details,requestId}`。
- 状态码：无权和不存在都返回 404；未登录 401；范围外写 403 `DATA_SCOPE_DENIED`；版本冲突 409。POST 支持 `Idempotency-Key`，可改资源带 `expectedVersion`。
- 会计按中国准则、人民币本位币；待定配置用演示默认值并注明"真实使用前需核实"。

## 3. 必须复用的共用函数（以 main 实际代码为准，禁止各模块自写一套）

| 用途 | 唯一入口 | 说明 |
|---|---|---|
| 权限判断 | `crosserp.platform.permissions.PermissionService`（`require`、`current_permissions`、`serialize`），请求内用 `get_permission_service(request)` 取 | 不按角色名、会话快照判断权限 |
| 店铺数据范围 | `PermissionService.store_scope(principal, entity)` → `crosserp.iam.scope.StoreScope`（`AllStores` 或 `frozenset[UUID]`）；查询里用 `crosserp.iam.scope.apply_store_scope(statement, column, scope)` | 缺规则、格式错、未知范围类型一律报错，不放行；空集返回空结果。不得自写 `_store_ids`、`allowed_store_ids`，不得"没有 storeIds 就放行" |
| 其他数据范围 | `PermissionService.data_scope_filter(principal, entity)` | 期间、法人等新范围类型在 IAM 里扩展，不在业务模块里另写 |
| 字段权限 | `PermissionService.serialize(...)`，成本字段按 `sku.cost:read` | 不在路由里手工删字段 |
| 写动作执行 | `crosserp.platform.factory.make_action_dispatcher(session, permission_service)`，在请求自己的 `with session.begin()` 里构造并 `dispatch` | 不直接 `ActionDispatcher(...)`，不用全局共享执行器；业务写入全部放进 business_action，dispatch 之前不得改会话 |
| 接口元数据与幂等归属 | `crosserp.api.metadata.api_endpoint(entity=, action=, permission=, risk_tier=, idempotency=)`，`idempotency` 取 `"dispatcher"`/`"http"`/`"none"` | 幂等记录按调用身份+方法+路由模板+请求体哈希隔离，回放在身份/权限/范围校验之后；HTTP 层在 `crosserp.api.idempotency`，动作层在 `crosserp.platform.idempotency`。不得在业务模块或共享中间件里写 `_replay_permitted`、`_defer_success_replay` 之类补丁，不得维护硬编码路由名单 |
| 审批提交 | `crosserp.platform.approval.ApprovalGateway.submit(...)` → `ApprovalSubmission`（`approval_id`、`state`、`resolution`，HTTP/审计都用 `to_payload()`） | 不写 `_ApprovalResult(dict)` 之类兼容壳，不用 `isinstance` 分支兼容旧返回 |
| 审计 | `crosserp.platform.audit.AuditRecorder.record(...)`（实现 `DefaultAuditRecorder`，由工厂注入） | 不绕开它直接写审计表 |
| 撤销 | medium 动作由 dispatcher 在同一事务写 `agent_undo`；动作可声明撤销函数，否则按 EntityVersion 回退；入口 `POST /agent/suggestions/{id}/undo` → `ActionDispatcher.undo` | 不支持的类型必须报错，不得静默成功；中风险动作缺实体 ID 必须报错 |
| 文件 | 平台 FileObject（记录 SHA-256），文件目录只有一个定义 | 不新增可选 `output_dir` 之类第二条路径 |
| 账务写出 | `ledger/write_service.py` 是唯一写出口，只生成草稿 | |

如果需要的能力共用函数里没有：先在进度文件写明原因和最小改动，在平台层扩展并补测试，**不得在业务模块里另起一套**，也不得在共享组件里按路径或实体开特例。

## 4. 禁止防御性编程（maken t155u，硬性）

- 按 08 v4 和功能文件直接实现。不为假想场景加兜底分支；不层层 try/except 吞错；不重复校验同一件事；不加可选参数或兼容开关；不保留旧路径的 fallback；不做过度的 None 检查。
- 具体禁止写法：`dict.get(key, 默认值)` 掩盖缺失数据、`getattr(obj, "x", 默认)`、`or {}`/`or []`、`hasattr` 兼容判断、`except ...: pass`、只记日志不抛出、无返回值的静默 `return`、返回假成功。
- 允许破坏性修改：旧接口、旧代码、旧表直接删改，不做双轨兼容。
- 错误显式抛出，用统一 `ErrorCode`。
- 不确定时按 08 v4 决定；不为"以防万一"扩大范围，也不因保守缩小功能，或把应有的执行权改成只读/草稿。
- 安全边界（权限、审批、审计、密钥、AI 风险分级、数据范围、幂等隔离）是设计本身，必须严格实现，不算防御性代码。
- 请求体用严格 Pydantic 模型（`extra="forbid"`）。
- 报告里单列"删掉的防御性/兼容代码"清单（文件 + 内容）。

## 5. 测试纪律

- 新功能必须按功能文件的验收标准补测试。每个接口至少覆盖：有权成功；无权 404；不存在 404；未登录 401；数据范围（读过滤、单条 404、写 403）；AI 按风险档的行为（medium 直接执行且有撤销记录；high 进审批且审批前业务数据不变；critical 拒绝）；幂等回放（同人同键同体回放、同键不同体 409、他人同键不可见、权限收回后回放 404）；`expectedVersion` 冲突 409；审计 `actor_type`/`on_behalf_of`；金额精度；写接口"请求结束后用全新 Session 能查到结果"。
- 可以为新设计更新编码了旧行为的测试，但必须在提交说明里逐条写理由。**不得为过关删除或放松权限、范围、审批、审计、幂等、撤销、风险档、密钥、退出登录等安全断言**；不得 skip/xfail 规避；不得调大超时；不得用 mock 冒充验收。
- 偶发失败只能原样重跑；同一测试连续两次失败按真问题定位，修实现，不改断言。
- 每块结束前在自己工作树跑（带隔离库环境变量，见第 6 节）：
  - `uv run ruff format --check .`、`uv run ruff check .`、`uv run mypy`
  - `uv run pytest -q`（全量，写明总数和 FAIL 数）；MySQL 自己库的 `uv run pytest -m db`
  - `uv run python scripts/check_doc_links.py`、`uv run python scripts/check_grants_cover_all_tables.py`、`uv run python scripts/check_api_contract.py`
  - `uv run python scripts/check_merge_guard.py --base <切出时的 main 提交>`（合并前自动检查，见 [acceptance.md](acceptance.md)）
  - 迁移往返 `upgrade head → downgrade base → upgrade head`（SQLite 必做，MySQL 测试实例可用时也做）
  - 密钥扫描无命中
- 影响前端时同步修改（复用 Vuexy/Vuetify 现有组件），在 `frontend` 跑 vue-tsc、eslint、vite build，构建后立即 `git checkout -- frontend/auto-imports.d.ts frontend/components.d.ts frontend/typed-router.d.ts`。前端默认仍为 mock 模式，现有 mock 行为和前端回归不得改变。`frontend/node_modules` 是联接，不要 `pnpm install`。

## 6. 测试数据库隔离（硬性）

- maken 的默认开发库是 `~/.crosserp/data.db`。**任何测试、迁移、脚本都不得使用它，也不得读取、修改、改名、删除 `~/.crosserp/` 下任何文件。** data.db 重建只在监督方指定的合并步骤里做（旧库只改名备份，不删除）。
- 运行任何 `uv run pytest`、alembic、`crosserp` 命令前，在同一条命令里设置 `$env:CROSSERP_DATABASE_URL` 和 `$env:CROSSERP_MIGRATE_DATABASE_URL`，指向本树专用临时 SQLite `sqlite:///%TEMP%/cx-pw/backend/db/<树名>.db`，或本树分配的 MySQL 库。
- MySQL 测试实例：127.0.0.1:3418，连接串见 `%TEMP%\cx-pw\backend\mysql84\test-url.txt`（本机一次性测试实例，允许读取），只把库名换成分配给你的库，不碰其他库。不可用就只做 SQLite，并在报告里写明。

## 7. 工作树、端口与提交

- 一个功能（或一组必须耦合开发的功能）一个 detached 工作树、一个开发 agent（grok CLI），独立端口、独立测试库。工作树在 `D:\make\write\work\CrossERP-wt\<树名>`。
- 迁移：接 main 当前 head，合并时线性化成单链；授权脚本 `grant_*.sql` 覆盖新表。
- 禁用端口：5173、8000、4173（maken 预览）、4184；只用分配给你的端口。不碰 4173 预览进程、不碰其他工作树、不杀未知进程。
- 不建命名分支，不打 tag，不 push，不 force，不 `reset --hard`，不 rebase/amend 已有提交（尤其是已被合入或被其他工作树当基线的提交），修正一律用新提交。
- `git commit` 一律 `-F <UTF-8 文件>`（文件放 `%TEMP%\cx-pw\backend\`），中文 Conventional Commit。不用 PowerShell `*>` 重定向。不提交 `_task/`、`last.txt`、日志、截图、临时脚本。
- 不改主仓库 `D:\make\write\work\CrossERP` 工作区（合并任务除外）。
- 拆工作树：先 `cmd /c rmdir` 删 `frontend\node_modules` 联接，再 `git worktree remove`（不加 `--force`）。
- 不读 `CrossERP演示密码.txt`、`.env`、任何密钥/令牌文件。
- 合入 main 后必须更新 [`docs/PROJECT_MEMORY.md`](../PROJECT_MEMORY.md) 的「当前状态」和新增决策（见该文件「更新规则」）。可与功能文件、[README](README.md) 进度表放在同一提交，或紧接着再提交一次。

## 8. 报告

用中文如实写：做了哪些功能（业务语言）；提交 SHA；接口清单及每个接口的风险档；破坏性改动清单；修改过的旧测试及逐条理由；删掉的防御性/兼容代码；各检查命令的退出码和 FAIL 数（含 MySQL、迁移往返、check_merge_guard 命中与豁免）；未实现项与需 maken 拍板的事项。没跑或失败的如实写，不说"应该通过"。进度写进 `%TEMP%\cx-pw\backend\<任务名>-progress.txt`。
