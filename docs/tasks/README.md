# CrossERP 任务说明（docs/tasks）

这里的每个文件是一个可以直接交给编码代理的任务。粒度：代理工作半天到 2 天。来源：`docs/plan/实施方案.md` 第 8 节 W1–W4（日期为估算）。

## 怎么用
1. 代理每次只做**一个**任务：状态为 `todo` 且依赖都为 `done` 的第一个（或 maken 指定的）。
2. 代理先读 `AGENTS.md`，再完整读任务文件，再读任务「背景」里引用的实施方案章节。
3. 直接在 `main` 上工作，状态改 `doing`；本项目只有一个开发代理，不创建任务分支或工作树。
4. 做完、本地验收命令全部跑过 → 状态改 `review`，填「完成记录」，按 AGENTS.md 直接提交到 `main`。
5. maken 按任务末尾的「人工验收清单」逐条检查 → 状态改 `done`（不需要合并分支）。
6. 卡住 → 状态改 `blocked`，在任务文件「问题」一节写清楚，等 maken 回复。

状态取值：`todo` → `doing` → `review` → `done`；任何时候可进入 `blocked`。**只有 maken 能把状态改成 `done`。**

## 状态表
| 编号 | 任务 | 周 | 估时 | 依赖 | 状态 |
|---|---|---|---|---|---|
| T01 | [仓库骨架：uv + pyproject + 规范工具](T01-repo-skeleton.md) | W1 | 0.5 天 | — | review |
| T02 | [FastAPI 最小服务：hello + /health](T02-fastapi-health.md) | W1 | 0.5 天 | T01 | review |
| T03 | [金额核心：Money + parse_amount](T03-core-money.md) | W1 | 1 天 | T01 | review |
| T04 | [数据库类型 + 会话 + MySQL 自检](T04-db-types-session.md) | W1 | 1.5 天 | T03 | review |
| T05 | [数据模型 + Alembic 迁移 + upsert](T05-schema-migrations.md) | W1 | 2 天 | T04 | review |
| T06 | [审计哈希链](T06-audit-chain.md) | W1 | 1 天 | T05 | review |
| T07 | [CI：三系统 × 三数据库](T07-ci-matrix.md) | W1 | 1 天 | T05 | review |
| T08 | [合成样本生成器（含边界情况）](T08-sample-generator.md) | W2 | 1.5 天 | T03 | review |
| T09 | [连接器协议 + 导入批次](T09-connector-base-import-batch.md) | W2 | 1.5 天 | T05 | review |
| T10 | [Amazon 结算 Flat File V2 导入器](T10-amazon-settlement-v2.md) | W2 | 2 天 | T08, T09 | review |
| T11 | [Shopify 打款 CSV 导入器](T11-shopify-payouts.md) | W2 | 1 天 | T08, T09 | review |
| T12 | [通用映射导入器（领星/赛狐/成本/汇率）](T12-generic-mapped.md) | W2 | 1.5 天 | T09 | review |
| T13 | [导入命令 + 端到端测试 + 真实文件试导入](T13-import-cli-golden.md) | W2 | 1 天 | T10, T11, T12 | review |
| T14 | [对账异常分类设计（文档）](T14-recon-categories-design.md) | W2 | 0.5 天 | T08 | review |
| T15 | [导入批次规则：失败可重导 + 打不开也留记录（⚠ 待 maken 确认）](T15-import-batch-rules.md) | W3 | 1 天 | T09, T13 | review |
| T16 | [三库实测：CI db-matrix 在 MySQL 8.4 / PG 18 跑通](T16-three-db-verify.md) | W3 | 1 天 | T07, T13 | review |
| T17 | [异常目录：原因码定稿 + 中文模板 + 候选码](T17-issues-catalog.md) | W3 | 0.5 天 | T14 | review |
| T18 | [对账引擎核心：规则注册表 + 确定性匹配](T18-recon-engine-core.md) | W3 | 2 天 | T16, T17 | review |
| T19 | [对账补充规则：待下期、多收费、拒付、部分退款、重复结算](T19-recon-timing-fees-refunds.md) | W3 | 1.5 天 | T18 | review |
| T20 | [利润计算：订单行 / SKU（成本生效期 + 汇率）](T20-profit-sku-order.md) | W3 | 2 天 | T18 | review |
| T21 | [标准答案比对：利润逐分 + 匹配率断言（指标 2、3）](T21-golden-eval.md) | W3 | 1 天 | T19, T20 | review |
| T22 | [报表输出：reconcile / profit --out report.xlsx](T22-cli-report-xlsx.md) | W3 | 1 天 | T20 | review |
| T23 | [只读网页：导入记录 / SKU 利润 / 异常清单](T23-web-readonly.md) | W3 | 1.5 天 | T22（T15 可选） | review |
| T24 | [crosserp demo + 基础安装（三系统）](T24-demo-basic-install.md) | W3 | 1 天 | T21, T23 | review |
| T25 | [v0.1 验收证据汇总](T25-v01-acceptance.md) | W3 | 0.5 天 | T16, T21, T24 | review |
| T26 | [发布 v0.1.0（暂缓：v1.0 前不发布）](T26-release-v01.md) | W3 | 0.5 天 | T25 | 暂缓（v1.0 前不发布） |
| T27 | [审批状态机 approval/](T27-approval-state-machine.md) | W4 | 1 天 | T26（maken 同意先开 W4） | review |
| T28 | [唯一写出口 write_service + 守卫测试（指标 4）](T28-write-service-guard.md) | W4 | 1.5 天 | T27 | review |
| T29 | [业务审计补全：字段 + 同事务 + 全动作](T29-audit-fields-transaction.md) | W4 | 1.5 天 | T06, T27 | review |
| T30 | [数据库账号权限 + 智能体只读会话](T30-db-grants-readonly-session.md) | W4 | 1 天 | T16, T29 | review |
| T31 | [审计导出 / 离线校验 / 保留 + W4 验收](T31-audit-export-retention.md) | W4 | 1.5 天 | T29, T30 | review |
| T32 | [用户 / 角色 / 会话表 + argon2 + `init` 建第一个管理员（⚠ 待 maken 确认）](T32-auth-tables-init-admin.md) | W5 | 1.5 天 | T31（maken 同意开 W5） | review |
| T33 | [网页登录 / 登出 / 会话 / CSRF / 登录锁定 + `config.py`（⚠ 待 maken 确认）](T33-login-session-csrf-lockout.md) | W5 | 1.5 天 | T32 | review |
| T34 | [登录/权限审计 security_event：独立哈希链 + 登录日志页 + 导出（⚠ 待 maken 确认）](T34-security-event-chain.md) | W5 | 1 天 | T33 | review |
| T35 | [权限 `require(permission)` + 权限矩阵参数化测试 + 职责分离 / 单人模式（⚠ 待 maken 确认）](T35-permissions-matrix.md) | W5 | 1.5 天 | T34 | review |
| T36 | [用户管理页（admin）](T36-user-admin-page.md) | W5 | 1 天 | T35 | review |
| T37 | [异常处理队列页：状态流转 + 写说明 + 查看原始行](T37-issue-queue-page.md) | W5 | 1 天 | T35 | review |
| T38 | [审批台 + 审计页（改前改后对比、链状态）+ W5 验收证据](T38-approval-console-audit-page.md) | W5 | 1.5 天 | T36、T37 | review |
| T39 | [凭证草稿：会计科目映射 `accounts.yaml` + `voucher` / `voucher_line` 表 + 借贷平衡（⚠ 待 maken 确认）](T39-voucher-model-accounts.md) | W6 | 2 天 | T38 | review |
| T40 | [写出目标重构 + 金蝶导入模板 `kingdee_xlsx`（表头可配置，⚠ 待真实模板验证）](T40-ledger-kingdee-xlsx.md) | W6 | 1.5 天 | T39 | review |
| T41 | [通用 Excel 目标 `generic_xlsx` + 网页「下载凭证」+ W6 验收证据（⚠ 待 maken 确认）](T41-generic-xlsx-download-w6.md) | W6 | 1.5 天 | T40 | review |
| T42 | [AI 只读工具层 `agent/tools.py`（只读账号）+ 规则文档检索（⚠ 待 maken 确认）](T42-agent-readonly-tools.md) | W7 | 1.5 天 | T41 | review |
| T43 | [AI 运行时：引用检查 + 数字核对 + `crosserp ask` + 提示词文件（⚠ 待 maken 确认）](T43-agent-runtime-ask.md) | W7 | 2 天 | T42 | review |
| T44 | [AI 调用记录：OTel → 数据库（`llm_call` / `llm_tool_call` / `prompt_version`）+ 费用表（⚠ 待 maken 确认）](T44-llm-observability-tables.md) | W7 | 1.5 天 | T43 | review |
| T45 | [发给模型前脱敏 + 提示注入防护 + AI 正文保留期（⚠ 待 maken 确认）](T45-redaction-injection-retention.md) | W7 | 1 天 | T44 | review |
| T46 | [网页 AI 问答页：引用可点开到原始行 + 审计](T46-web-ask-page.md) | W7 | 1 天 | T45 | review |
| T47 | [MCP 服务（只读工具）+ API token 鉴权与安全事件（⚠ 待 maken 确认）](T47-mcp-server-api-token.md) | W8 | 1.5 天 | T46 | todo |
| T48 | [AI 监控页：调用量、费用、拒答率、慢调用](T48-llm-monitor-page.md) | W8 | 1 天 | T47 | todo |
| T49 | [AI 预算与告警：超额横幅 + 硬拒绝 + 演示脚本 + W8 验收证据（⚠ 待 maken 确认）](T49-llm-budget-alert-w8.md) | W8 | 1.5 天 | T48 | todo |
| T50 | [AI 评测集：20 个问题 + pydantic-evals 评分（⚠ 待 maken 确认）](T50-eval-question-set.md) | W9 | 1.5 天 | T49 | todo |
| T51 | [评测记录入库 + 基线对比 + CI 离线评测（⚠ 待 maken 确认）](T51-eval-run-ci.md) | W9 | 1 天 | T50 | todo |
| T52 | [Docker Compose 部署：SQLite / PostgreSQL / MySQL 三种 profile（不推镜像）（⚠ 待 maken 确认）](T52-docker-compose.md) | W9 | 1.5 天 | T51 | todo |
| T53 | [安装矩阵计时：三系统从零到看到首页（不经 PyPI）（⚠ 待 maken 确认）](T53-install-matrix-timing.md) | W10 | 1 天 | T52 | todo |
| T54 | [质量门槛提高：覆盖率 80%、mypy 覆盖新模块（⚠ 待 maken 确认）](T54-coverage-mypy-hardening.md) | W10 | 1.5 天 | T53 | todo |
| T55 | [文档：中英文 README、架构图、安全/可观测/数据库文档、ADR、贡献与安全说明（⚠ 待 maken 确认）](T55-docs-adr-zh.md) | W10 | 1.5 天 | T54 | todo |
| T56 | [v0.5 内部验收：指标 1–6 + 新增验收项 A–F 证据汇总（⚠ 待 maken 确认）](T56-v05-internal-acceptance.md) | W10 | 1 天 | T55 | todo |

T01–T14：已合并到 main，状态 `review`（maken 本地只在 SQLite 上验收过；MySQL / PostgreSQL 由 T16 补测，T16 通过后 maken 再把 T01–T14 改成 `done`）。

工作量（估算）：T01–T14 约 16.5 个代理工作日；W3（T15–T26）约 13.5 天；W4（T27–T31）约 6.5 天。实施方案按每周兼职 10–15 小时估算（「估算」），W3、W4 各一周大概率装不下，**顺延很正常**，以验收通过为准，不赶工。

建议顺序：
- W3：T16 → T17 → T18 → T19 → T20 → T21 → T22 → T23 → T24 → T25 → T26。
- T15 等 maken 在任务文件「问题」一节确认两条决定后插队做（越早越好，T23 的导入记录页会用到它的字段）；T17 开工前 maken 要先勾选 T14 的 5 个候选原因码。
- W4：T27 → T28 → T29 → T30 → T31（T27 需要 v0.1 已发布，或 maken 明确同意先开 W4）。

需要 maken 先拍板才能开工 / 完成的事项（代理遇到会把状态改 `blocked`）：
| 任务 | 要确认的事 |
|---|---|
| T15 | 失败批次能否同文件重导；打不开的文件是否落失败批次 |
| T17 | T14 的 5 个候选码 `FEE_OVERCHARGE`、`SETTLEMENT_DELAYED`、`CHARGEBACK`、`PARTIAL_REFUND`、`DUPLICATE_SETTLEMENT` 各要不要 |
| T18 | Shopify 按整单匹配；重跑对账保留旧结果 |
| T19 | 多收费容差（绝对值/百分比）；拒付是否单列 |
| T20 | 退款是否回库（影响成本）；非订单费用是否分摊；舍入规则 |
| T21 | 手算 20 个真实 SKU 的标准答案 |
| T26 | PyPI 名字、trusted publisher 配置、打 tag 发布（只有 maken 能做） |

人工验收命令的写法：清单里统一写 `uv run crosserp ...`。T24 完成前如果 `uv run crosserp` 在你电脑上不能用，就按 T13 的方式运行，二者等价：先 `$env:PYTHONPATH="D:\make\write\work\CrossERP\src"`，再把 `uv run crosserp` 换成 `& .\.venv\Scripts\python.exe -m crosserp.cli`。

W5–W10（T32–T56，v0.5 内部验收）已按 T31 完成时的仓库实际状态拆好，目标是内部验收，不是发布。

建议顺序：W5 为 T32 → T33 → T34 → T35 → T36 / T37 → T38；之后依次完成 W6–W10 的 T39–T56。

**v1.0 前不发布**：T32–T56 不打 tag、不发 PyPI / GHCR / Docker Hub、不建 GitHub Release、不推公开仓库；T26 暂缓。

## 任务文件模板
新建任务时复制下面内容到 `T<编号>-<短名>.md`：

```markdown
# T<编号> <任务标题>

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| todo | W? | ? 天 | T?? | `main` |

## 目标
（一两句话：做完以后用户/系统能做到什么）

## 背景
（引用实施方案章节号；外部格式附官方来源链接；未核实/推断的地方明确标注）

## 范围
（要做的东西，精确到函数名、文件名、字段名、错误码）

## 不做
（明确排除的内容，防止代理越界）

## 步骤
1. （先写测试 / 期望值从哪里来）
2. ...

## 涉及文件
（只允许改这些；要改别的，PR 里说明原因）

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest ... -q` | passed |

## maken 人工验收清单
- [ ] （用大白话写，命令可以直接复制到 PowerShell）

## 问题
（代理遇到疑问写在这里，并把状态改为 blocked）

## 完成记录
（代理填写：实际运行的命令 + 输出摘要 + PR 链接；maken 填写验收日期）
```
