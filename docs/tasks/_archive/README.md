# CrossERP 开发任务索引

> **已归档（2026-11-12）：** 本页是旧任务索引，只作历史记录。现行后端任务、规则和进度见 [docs/tasks/README.md](../README.md)。

> **适用范围与状态：** 本目录包含早期 T01–T56 历史任务卡，以及按 08 v4 重排的 [P0–P5 后端任务卡](backend-phases.md)。T01–T56 的“已完成”表示代码或任务提交已存在；“部分”表示实现存在但真实数据、远程 CI、模型或人工证据仍有边界；“已被 08 v4 取代”表示不再作为现行开发依据。当前后端唯一依据是 [08-后端模块与 API 设计](../../design/08-后端模块与API设计.md) 及其 [实体目录](../../design/08/ontology-entities.yaml)、[OpenAPI 草案](../../design/08/openapi-draft.yaml)。

## 使用方式

1. 新开发按 [backend-phases.md](backend-phases.md) 的 P0–P5 顺序执行；一次只做一张卡。
2. 先读 [AGENTS.md](../../../AGENTS.md)，再读任务卡和 08 v4 对应章节。
3. 任务卡中的历史验收命令只用于复核历史实现；新增接口必须补权限、审计、三路径一致性、mock 点击和密钥扫描验收。
4. 任务状态由 maken 人工把 review 改为 done；真实数据、远程 CI 或模型未核实的项不得写成“通过”。

## T01–T56 总表

| 编号 | 标题 | 状态 | 对应 08 模块 |
|---|---|---|---|
| T01 | [仓库骨架：uv + pyproject + 规范工具](T01-repo-skeleton.md) | 已完成 | platform/db |
| T02 | [FastAPI 最小服务：hello 页 + /health](T02-fastapi-health.md) | 已完成 | web/platform |
| T03 | [金额核心：Money + parse_amount](T03-core-money.md) | 已完成 | core |
| T04 | [数据库层：Money4 / FxRate / UtcDateTime 类型 + 连接会话 + MySQL 启动自检](T04-db-types-session.md) | 已完成 | db |
| T05 | [数据模型：v0.1 业务表 + Alembic 初始迁移 + upsert](T05-schema-migrations.md) | 已完成 | db |
| T06 | [审计日志：只追加哈希链 append / verify_chain](T06-audit-chain.md) | 已完成 | audit |
| T07 | [CI：三系统 × Python 3.12/3.14 + 三数据库矩阵](T07-ci-matrix.md) | 已完成 | ci |
| T08 | [合成样本生成器：121 单 + 结算/打款文件 + 故意埋的边界情况](T08-sample-generator.md) | 已完成 | samples |
| T09 | [连接器协议 + 注册表 + 导入批次（sha256 去重、坏行不中断）](T09-connector-base-import-batch.md) | 已完成 | connectors/ingest |
| T10 | [Amazon 结算报告 Flat File V2 导入器 + 费用分类表](T10-amazon-settlement-v2.md) | 已完成 | connectors/settlement |
| T11 | [Shopify Payments 打款 CSV 导入器](T11-shopify-payouts.md) | 已完成 | connectors/settlement |
| T12 | [通用映射导入器：领星 / 赛狐 / 成本表 / 汇率表 / SKU 映射](T12-generic-mapped.md) | 已完成 | connectors/ingest |
| T13 | [导入命令 `crosserp import` + 全样本端到端测试 + 真实文件试导入](T13-import-cli-golden.md) | 已完成 | ingest/cli |
| T14 | [对账异常分类设计（为 W3 做准备，只写文档和枚举草案）](T14-recon-categories-design.md) | 已完成 | issues/reconciliation |
| T15 | [导入批次规则：失败批次可重导 + 打不开的文件也留失败记录（⚠ 待 maken 确认）](T15-import-batch-rules.md) | 已完成 | ingest |
| T16 | [三库实测：CI db-matrix 在 MySQL 8.4 / PostgreSQL 18 跑通（历史验收口径）](T16-three-db-verify.md) | 部分 | db/ci |
| T17 | [异常目录：原因码枚举定稿 + 中文模板 + 候选码落地](T17-issues-catalog.md) | 已完成 | issues |
| T18 | [对账引擎核心：规则注册表 + 订单号/SKU 确定性匹配](T18-recon-engine-core.md) | 已完成 | reconciliation |
| T19 | [对账补充规则：在途/待下期、多收费、拒付、部分退款、重复结算](T19-recon-timing-fees-refunds.md) | 已完成 | reconciliation |
| T20 | [利润计算：订单行 / SKU 利润（成本按生效期、月汇率折人民币）](T20-profit-sku-order.md) | 已完成 | profit |
| T21 | [标准答案比对：利润逐分一致 + 匹配率/异常原因断言（指标 2、3）](T21-golden-eval.md) | 已完成 | evals |
| T22 | [报表输出：`reconcile` / `profit --out report.xlsx`](T22-cli-report-xlsx.md) | 已完成 | web/reports |
| T23 | [只读网页：导入记录 / SKU 利润 / 异常清单](T23-web-readonly.md) | 已完成 | web |
| T24 | [`crosserp demo` + 基础安装（`uv tool install` 三系统可用）](T24-demo-basic-install.md) | 已完成 | cli/demo |
| T25 | [v0.1 验收：指标 2、3 + 基础安装 + 三库（历史验收口径），汇总证据](T25-v01-acceptance.md) | 部分 | evals/evidence |
| T26 | [发布 v0.1.0：release.yml + PyPI Trusted Publishing（发布动作由 maken 操作）](T26-release-v01.md) | 已被 08 v4 第 8 节取代 | release（已取代） |
| T27 | [审批状态机 `approval/`](T27-approval-state-machine.md) | 已完成 | approval |
| T28 | [唯一写出口 `ledger/write_service.py` + 守卫测试（指标 4）](T28-write-service-guard.md) | 已完成 | ledger |
| T29 | [业务审计补全：字段齐全 + 与业务修改同一事务 + 全动作覆盖](T29-audit-fields-transaction.md) | 已完成 | audit |
| T30 | [数据库账号权限（MySQL/PG）+ 智能体只读会话](T30-db-grants-readonly-session.md) | 已完成 | db/agent |
| T31 | [审计导出 / 离线校验 / 保留策略 + W4 验收（指标 4）](T31-audit-export-retention.md) | 已完成 | audit |
| T32 | [用户 / 角色 / 会话表 + argon2 + `init` 建第一个管理员（⚠ 待 maken 确认）](T32-auth-tables-init-admin.md) | 已完成 | auth |
| T33 | [网页登录 / 登出 / 会话 / CSRF / 登录锁定 + `config.py`（⚠ 待 maken 确认）](T33-login-session-csrf-lockout.md) | 已完成 | auth/web |
| T34 | [登录/权限审计 security_event：独立哈希链 + 登录日志页 + 导出（⚠ 待 maken 确认）](T34-security-event-chain.md) | 已完成 | audit/security |
| T35 | [权限 `require(permission)` + 权限矩阵参数化测试 + 职责分离 / 单人模式（已被 08 v4 取代；⚠ 待 maken 确认）](T35-permissions-matrix.md) | 已完成 | iam |
| T36 | [用户管理页（admin）](T36-user-admin-page.md) | 已完成 | auth/web |
| T37 | [异常处理队列页：状态流转 + 写说明 + 查看原始行](T37-issue-queue-page.md) | 已完成 | issues/web |
| T38 | [审批台 + 审计页（改前改后对比、链状态）+ W5 验收证据](T38-approval-console-audit-page.md) | 已完成 | approval/audit |
| T39 | [凭证草稿：会计科目映射 `accounts.yaml` + `voucher` / `voucher_line` 表 + 借贷平衡（⚠ 待 maken 确认）](T39-voucher-model-accounts.md) | 已完成 | vouchers |
| T40 | [写出目标重构 + 金蝶导入模板 `kingdee_xlsx`（表头可配置，⚠ 待真实模板验证）](T40-ledger-kingdee-xlsx.md) | 已完成 | ledger |
| T41 | [通用 Excel 目标 `generic_xlsx` + 网页「下载凭证」+ W6 验收证据（⚠ 待 maken 确认）](T41-generic-xlsx-download-w6.md) | 已完成 | ledger/web |
| T42 | [AI 只读工具层 `agent/tools.py`（只读账号）+ 规则文档检索（⚠ 待 maken 确认）](T42-agent-readonly-tools.md) | 已完成 | agent |
| T43 | [AI 运行时：引用检查 + 数字核对 + `crosserp ask` + 提示词文件（⚠ 待 maken 确认）](T43-agent-runtime-ask.md) | 已完成 | agent |
| T44 | [AI 调用记录：OTel → 数据库（`llm_call` / `llm_tool_call` / `prompt_version`）+ 费用表（⚠ 待 maken 确认）](T44-llm-observability-tables.md) | 已完成 | observability |
| T45 | [发给模型前脱敏 + 提示注入防护 + AI 正文保留期（⚠ 待 maken 确认）](T45-redaction-injection-retention.md) | 已完成 | agent |
| T46 | [网页 AI 问答页：引用可点开到原始行 + 审计](T46-web-ask-page.md) | 已完成 | agent/web |
| T47 | [MCP 服务（只读工具）+ API token 鉴权与安全事件（⚠ 待 maken 确认）](T47-mcp-server-api-token.md) | 已完成 | mcp_server |
| T48 | [AI 监控页：调用量、费用、拒答率、慢调用](T48-llm-monitor-page.md) | 已完成 | observability/web |
| T49 | [AI 预算与告警：超额横幅 + 硬拒绝 + 演示脚本 + W8 验收证据（⚠ 待 maken 确认）](T49-llm-budget-alert-w8.md) | 已完成 | observability |
| T50 | [AI 评测集：20 个问题 + pydantic-evals 评分（⚠ 待 maken 确认）](T50-eval-question-set.md) | 已完成 | evals |
| T51 | [评测记录入库 + 基线对比 + CI 离线评测（⚠ 待 maken 确认）](T51-eval-run-ci.md) | 已完成 | evals/ci |
| T52 | [Docker Compose 部署：SQLite / PostgreSQL / MySQL 三种 profile（历史并列目标，现行主库见 08 v4 第 11.3 节；不推镜像）（⚠ 待 maken 确认）](T52-docker-compose.md) | 已完成 | deploy |
| T53 | [安装矩阵计时：三系统从零到看到首页（不经 PyPI）（⚠ 待 maken 确认）](T53-install-matrix-timing.md) | 部分 | deploy/ci |
| T54 | [质量门槛提高：覆盖率 80%、mypy 覆盖新模块（⚠ 待 maken 确认）](T54-coverage-mypy-hardening.md) | 已完成 | ci |
| T55 | [文档：中英文 README、架构图、安全/可观测/数据库文档、ADR、贡献与安全说明（⚠ 待 maken 确认）](T55-docs-adr-zh.md) | 已完成 | docs |
| T56 | [v0.5 内部验收：指标 1–6 + 新增验收项 A–F 证据汇总（⚠ 待 maken 确认）](T56-v05-internal-acceptance.md) | 部分 | evals/evidence |
## 状态解释

- **已完成：** 当前仓库能找到对应实现或任务提交，但不替代人工验收。
- **部分：** 已有实现或历史证据，但至少一项真实数据、远程 CI、跨平台、模型或人工证据未核实。
- **已被 08 v4 取代：** 旧卡片原文保留，开头有取代标注；现行要求以 08 v4 和 [backend-phases.md](backend-phases.md) 为准。

T01–T56 的正文不重写。每张卡开头新增“当前状态”和“现行依据”；与已拍板决定冲突的旧要求以“取代标注”保留，避免代理按过时要求实现。T26 的发布动作暂停，符合 v1.0 前不发布规则。
