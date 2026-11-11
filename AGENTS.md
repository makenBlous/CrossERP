# CrossERP 开发代理入口

## 项目与当前状态

CrossERP 是面向跨境电商卖家的 ERP：把平台结算和业务文件导入系统，使用确定性代码完成清洗、对账、异常分析、SKU 利润和凭证流程，并以审批和操作日志保护写入动作。正式环境以 MySQL 8.4 LTS 为主库；本机演示保留 SQLite，PostgreSQL 只在明确满足替换条件时采用，详见 [后端模块与 API 设计](docs/design/08-后端模块与API设计.md) 第 11 章。

当前事实按下面三类阅读，不要把设计稿当成已交付功能：

| 状态 | 当前内容 |
| --- | --- |
| **已实现** | `src/crosserp/` 中的 Python/FastAPI 后端已有文件导入、对账、利润、凭证、审批、操作审计、登录会话、AI 只读工具和 MCP；现有网页入口是 Jinja 路由。具体以代码和测试为准。 |
| **仅静态原型（前端 mock）** | `frontend/` 是 Vue 3 + TypeScript + Vuetify 3 + Vite + 本地 Vuexy v10.11.1 参考的静态页面；其 API service 仍使用 mock，不能声称已接入后端。 |
| **仅设计** | Vue 前端所需的 `/api/v1` JSON 接口、实体动作目录、后续业务域和 agent worker 方案，见 08 v4、实体目录和 OpenAPI 草案。 |

后端已实现的业务目前还没有给 Vue 前端提供 JSON 接口；新增接口必须先遵循 [后端模块与 API 设计](docs/design/08-后端模块与API设计.md) 及其配套 OpenAPI，不要从页面 mock 反推接口。

## 开始前的阅读顺序

1. [全仓文档索引](docs/README.md)：先确认事实来源和文档状态。
2. [设计方案索引](docs/design/README.md)：了解 00–08 的关系。
3. [后端模块与 API 设计](docs/design/08-后端模块与API设计.md)：后端与 agent 的唯一接口依据。
4. [后端开发指南](docs/backend/README.md)：包边界、动作执行器、权限、迁移和 MySQL 规则。
5. [前端文档索引](frontend/docs/README.md)：静态原型、组件复用和接口切换方式。
6. [业务域索引](docs/domains/README.md)：实体、流程和业务口径。
7. [开发任务路线](docs/tasks/backend-phases.md)：按 P0–P5 排序的任务卡。
8. [开发规则](docs/dev/开发规则.md)：工作树、权限、金额、AI 安全和文档纪律。

## 已拍板决定（一句话）

采用 MySQL 主库的模块化单体，以本体实体和动作作为统一入口；原件先清洗、校验、去重再投射，网页、CLI、agent 和定时任务共用权限检查，DeerFlow 以独立 worker 的 SDK 方式嵌入，AI 继承登录人权限且不执行代码，钱账改动必须经过审批。完整决定与例外以 [08 v4 第 12 章](docs/design/08-后端模块与API设计.md#12-已决定与待拍板) 为准。

## 硬规则

- 金额由确定性代码计算，使用 `Money = {amountMinor: int64, currency}`，`SCALE = 10000`；AI 只解释、建议和引用数据。
- 凭证、付款、调账等改账动作只能进入草稿或待审，唯一写出口和审批规则见 08；不能自己审批自己的单据。
- agent 权限不超过当前登录人；AI 不能执行代码、不能使用 bash 或沙箱。关闭 AI 后人工流程必须可用。
- 原始数据不可改，审计只追加；任何密钥、密码、token 和真实卖家数据都不得进入仓库。
- 发现规则与 08 v4、OpenAPI 或实体目录冲突时，暂停实现并报告，不自行发明第三套口径。

## 工作入口

从分离头工作树开始：`git worktree add --detach <path> main`。不创建任务分支，不改其他工作树。提交前按 [测试与回归](docs/dev/测试与回归.md) 做完整检查；提交信息遵循中文 Conventional Commits。不要打 tag、发 Release、强制推送或重写已推送历史。

## 保留的工程约束

- 方案中的 agent-erp / agent_erp 已改名：仓库与包是 crosserp，Python 包是 src/crosserp，CLI 是 crosserp，环境变量使用 CROSSERP_ 前缀，默认 SQLite 路径是 ~/.crosserp/data.db。
- 固定技术栈是 Python 3.12+、uv、FastAPI、SQLAlchemy、Alembic、Pydantic、Typer、python-calamine、openpyxl、pytest、ruff 和 mypy；换框架、数据库或依赖前先报告。
- 金额只用 Money / Decimal，字符串金额只经 parse_amount()；中间计算不提前舍入。时间带时区并以 UTC 存储；数据库读写放在 db/repo，业务代码不写原生 SQL。
- 连接器按表头取列；未知列和费用类型生成异常，不丢数据、不猜；标准记录保留 connector_id、connector_version、import_batch_id、source_file、row_no provenance。
- 三库兼容使用 SQLAlchemy 通用类型；金额列使用 Money4，汇率使用 FxRate，字符串索引列不超过 255；方言差异集中在 db/dialects.py。MySQL 连接串使用 charset=utf8mb4，并检查 8.4、utf8mb4 和 STRICT_TRANS_TABLES。
- 审计日志只追加，哈希为 sha256(prev_hash + 规范化 JSON)；不通过审批不写账；LLM 不计算金额、不改匹配结果、不改利润。
- v1.0 前不发布 PyPI、容器镜像或公开 Release；不把密钥和真实卖家数据放入仓库。测试失败时修实现并保留证据，不改测试让 CI 变绿。
