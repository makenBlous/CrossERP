# CrossERP 任务说明（docs/tasks）

这里的每个文件是一个可以直接交给编码代理的任务。粒度：代理工作半天到 2 天。来源：`docs/plan/实施方案.md` 第 8 节 W1/W2（日期为估算）。

## 怎么用
1. 代理每次只做**一个**任务：状态为 `todo` 且依赖都为 `done` 的第一个（或 maken 指定的）。
2. 代理先读 `AGENTS.md`，再完整读任务文件，再读任务「背景」里引用的实施方案章节。
3. 开分支 `task/T<编号>-<短名>`，状态改 `doing`。
4. 做完、本地验收命令全部跑过 → 状态改 `review`，填「完成记录」，开 PR。
5. maken 按任务末尾的「人工验收清单」逐条检查 → 合并 PR → 状态改 `done`。
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
| T06 | [审计哈希链](T06-audit-chain.md) | W1 | 1 天 | T05 | todo |
| T07 | [CI：三系统 × 三数据库](T07-ci-matrix.md) | W1 | 1 天 | T05 | todo |
| T08 | [合成样本生成器（含边界情况）](T08-sample-generator.md) | W2 | 1.5 天 | T03 | review |
| T09 | [连接器协议 + 导入批次](T09-connector-base-import-batch.md) | W2 | 1.5 天 | T05 | todo |
| T10 | [Amazon 结算 Flat File V2 导入器](T10-amazon-settlement-v2.md) | W2 | 2 天 | T08, T09 | todo |
| T11 | [Shopify 打款 CSV 导入器](T11-shopify-payouts.md) | W2 | 1 天 | T08, T09 | todo |
| T12 | [通用映射导入器（领星/赛狐/成本/汇率）](T12-generic-mapped.md) | W2 | 1.5 天 | T09 | todo |
| T13 | [导入命令 + 端到端测试 + 真实文件试导入](T13-import-cli-golden.md) | W2 | 1 天 | T10, T11, T12 | todo |
| T14 | [对账异常分类设计（文档）](T14-recon-categories-design.md) | W2 | 0.5 天 | T08 | review |

合计约 16.5 个代理工作日（估算）。实施方案按每周兼职 10–15 小时估算（「估算」），W1/W2 可能装不下，**顺延到 W3 很正常**，以验收通过为准，不赶工。

建议顺序：T01 → T02 → T03 → T04 → T05 → T06 → T07 → T08 → T14 → T09 → T10 → T11 → T12 → T13。T08、T14 不依赖数据库，可与 T04–T07 并行（如果你同时开两个代理）。

W3 及以后的任务（对账、利润、网页报表、发布 v0.1）等 W2 验收后再拆，避免提前定死细节。

## 任务文件模板
新建任务时复制下面内容到 `T<编号>-<短名>.md`：

```markdown
# T<编号> <任务标题>

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W? | ? 天 | T?? | `task/T<编号>-<短名>` |

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
