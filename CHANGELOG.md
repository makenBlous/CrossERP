# Changelog

本文件格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

- 前端补齐批次 A：新增 EX01–EX07、F23–F34 共 19 个财务与费用页面；补齐报销审批、借款冲抵、订单到凭证、利润期间选择、成本结转、结账拦截和预算预警静态流程。
- 前端第 2 批：财务 22 / 广告 4 / 审批 4 共 30 个静态页面完成；演示角色使用独立身份，服务层强制「提交人不能审批自己的单据」；凭证审批→导出、驳回重提、利润生成凭证、广告导入与按活动分摊（合计 100%）、费用映射确认、收付款多选核销审批流程均可在浏览器走通。
- 批次二前端重做：财务/广告/审批数据统一进入可持久化 mockdb，金额保持万分位整数，补齐状态字典、英文文案、详情空态和凭证审批导出链路。
- 修复登录页 CSRF：表单写入本次签发的令牌，刷新和多标签页可以登录；纯文本错误声明 UTF-8，避免中文 Windows 把「校验失败」显示成乱码。
- 修正本地 Docker Compose 通过 HTTP 访问时的登录 Cookie 配置；HTTPS 部署仍可设置 `CROSSERP_COOKIE_SECURE=1`。
- 安装 smoke 在跨平台启动本地服务时显式关闭 HTTPS Cookie，并在服务提前退出时立即报告原因。
- 安装 smoke 的本地 wheel 工具安装遇到瞬时下载失败时最多重试三次，最终仍必须成功。
- 安装 smoke 在 Windows 上会结束 uv 启动器留下的子进程，并等待 SQLite 文件锁释放后再删除临时库。

- 第 3 批组件复用审计：智能体/审计页面拆分到 src/views，CRM 看板改用 Vuexy FormKit 拖拽，删除 ModuleTable/StageBoard 重复封装。

### 新增

- 前端智能体中心与审计安全页面：对话建议进入审批、运行/用量/评测/知识库/提示词、DeerFlow mock 接入、审计哈希校验与导出。
- 前端第 3 批 CRM、系统设置和账户页面：线索/商机/工单流程、角色菜单覆盖、平台连接、Token 与会话管理。
- 新增 CRM、管理员和账户演示种子数据及审计记录，所有页面继续使用本地 mock API。

- 0.5.0 内部验收证据：`docs/evidence/v0.5.md`。未发布、未打 tag。

- T33 网页登录、服务器端会话、CSRF、失败登录锁定、非本机监听确认，以及环境变量/TOML 配置读取。
- T34 独立 security_event 哈希链、登录事件记录、安全日志页和安全审计包导出。
- T35 固定角色权限矩阵、网页权限检查、无权限安全事件和单人模式自审批基础保护。
- T36 管理员用户列表与创建用户页面。
- T37 异常状态流转服务和异常详情处理端点。
- W5 T32 用户、角色、会话、API token、系统设置表；Argon2id 密码哈希；`crosserp init` 首次创建管理员；`crosserp user` 用户管理命令。
- MySQL/PG 授权脚本支持全新账号首次执行，并覆盖审计导出和 W5 认证表权限。
- 对账异常分类草案 `docs/rules/recon-categories.md`，以及原因码人话模板草稿。5 个原因码已由 maken 于 2026-11-02 确认。
- v0.1 业务表、初始迁移和 `crosserp init`。已确认的 5 个原因码写入 `IssueKind`。
- GitHub Actions：三系统测试，以及 SQLite / MySQL 8.4 / PostgreSQL 18 检查。
- 导入协议、连接器注册表和按 sha256 去重的导入批次。坏行记 `PARSE_ERROR` 后继续。
- 只追加审计哈希链，以及 `crosserp audit verify`。
- 通用映射导入器，可读 YAML 列映射的订单、成本、汇率和 SKU。领星、赛狐表头仍待真实数据验证。
- Shopify Payments 打款 CSV 导入器。
- Amazon Settlement Flat File V2 导入器。
- `crosserp import`、`crosserp demo-import` 和 `crosserp issues list`。
- 失败批次可以重导。文件打不开也记一条失败批次，`sha256` 留空。
- 金额类型 `Money` 与 `parse_amount()`。全程 `Decimal`，禁止 float。
- 数据库类型 `Money4`、`FxRate`、`UtcDateTime`，以及 `crosserp db check`。当前默认 SQLite，切换库只改配置文件。
- 固定种子合成样本生成器，以及 `samples/synthetic/` 标准答案。
- `crosserp serve` 启动本机网页（默认只监听 127.0.0.1:8000）。首页显示「CrossERP 运行中」和版本号，`/health` 返回 `{"status":"ok","version":"0.0.1"}`。
- 运行依赖增加 `uvicorn`（只写下限），用于启动 FastAPI。页面引用官方 npm 包 htmx.org 2.0.11 的 `htmx.min.js`，未做交互。
- 初始化可安装的 `crosserp` 空包，并提供 `crosserp --version`。
- 三库实测文档、Docker 启动脚本和跨 SQLite/MySQL 8.4/PostgreSQL 18 的金额、时间、字符与迁移往返测试；修复 MySQL 初始迁移回滚时外键索引删除顺序。
- 导入批次规则：只有成功批次按 sha256 拒绝重复，失败批次可重导并保留重试关系；打不开的文件留失败记录，running 批次可手动标记失败。
- 原因码正式目录 `issues/catalog.yaml`、中文说明渲染和统一异常写入服务；`crosserp issues list` 显示原因名称与人话模板。
- 确定性的对账引擎核心：按平台订单号/SKU 分组匹配、规则注册表、可追溯的 `recon_run`，以及未匹配原因码和重跑保留旧结果。
- 对账补充规则：待下期、配送费多收费、拒付、部分退款和重复结算；新增配送费参考导入和 `reconcile` 摘要统计。
- 确定性利润计算：订单/SKU 原币与人民币利润、成本生效期、月汇率、缺成本/缺汇率异常、输入哈希和可复用利润快照。
- Golden 逐分比对命令 `crosserp check-golden`、合成利润/异常标准答案和差异报告。
- Excel/CSV 利润报表、异常清单和说明页；`reconcile --json` 机器可读输出。
- 只读网页：导入记录、SKU 利润、异常清单和本地静态 HTMX；所有业务路由仅 GET，服务固定监听 127.0.0.1。
- `crosserp demo --check` 独立演示库、包内合成样本、`python -m crosserp` 和三系统安装 smoke CI。
- W4 审批状态机：审批哈希锁定、一次性 token、内容变更自动失效、乐观锁和 CLI 审批命令。
- W4 唯一写出口：XLSX 导出必须使用未消费的有效审批 token，拒绝动作写入独立审计记录并防止重复导出。
- W4 业务审计补全：新增审计显示名和哈希版本兼容、对账/利润摘要审计、事务内审计辅助器和超长原因拒绝。
- W4 数据库权限：新增 MySQL/PG 三账号授权模板和智能体只读会话，SQLite 使用 `mode=ro`。
- W4 审计导出：生成 JSONL/CSV 审计包、manifest 和离线校验，新增检查点但不自动删除日志。
- W5 T38：审批台、利润报表提交审批、改前改后审计差异、业务与 security 哈希链状态和网页审计包导出。
- W6 T39：凭证草稿模型、科目映射 YAML、按月确定性生成、借贷平衡校验、凭证审批哈希和 CLI。
- W6 T40：唯一写出口按审批对象和目标分发，新增可配置常见列 `kingdee_xlsx` 凭证导出。
- W6 T41：通用双表凭证 Excel、网页凭证列表/详情和审批后双格式下载，未批准下载返回 403 并审计。
- W7 T42：只读智能体工具、金额引用、利润比较和规则 Markdown 关键词检索；默认只读 SQLite URI 修复。
- W7 T43：提示词版本、数字来源校验、OpenAI 兼容运行时和 `crosserp ask` 未配置提示。
- W7 T44：AI 调用、提示词版本和工具调用表，以及 Decimal 费用估算配置。
- W7 T45：模型上下文 PII 脱敏、数据标签注入边界和 AI 正文保留期清理命令。
- W7 T46：网页问一问、AI 权限/限流、白名单原始行查看和问答摘要审计。
- W8 T47：MCP 只读工具白名单、个人 API token 和 stdio 服务入口。
- W8 T48：AI 调用监控统计、慢调用列表和调用详情页。
- W8 T49：AI 金额/token 预算检查、阈值告警和预算设置命令。
- W9 T50：20 道经 maken 审核的离线评测题、确定性评分器和 `crosserp eval run --model test`。
- W9 T51：评测结果基线比较、eval_run 迁移和离线/手动模型 CI 工作流。
- W9 T52：SQLite / PostgreSQL / MySQL Compose profiles、长文本三库迁移、授权覆盖守卫和本地镜像部署文档。
- W10 T53：本地 wheel 三系统安装、初始化、demo、网页登录计时和 CI artifact 证据。
- W10 T54：覆盖率门槛提高到 80%，补充质量门槛测试和严格 mypy 校验。

## [0.1.0] - 未发布

### 已完成

- 文件导入、确定性对账、SKU 利润、Golden 比对、Excel/CSV 报表和只读网页。
- SQLite、MySQL 8.4、PostgreSQL 18 兼容验证。

### 已知限制

- 未含广告；非订单费用不分摊到 SKU。
- 拒付与退款按当前 v0.1 口径处理，真实数据仍需 maken 验收。
- 真实 20 个 SKU 手算答案和真实卖家数据尚未提交。


