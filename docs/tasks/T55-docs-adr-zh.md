# T55 文档：中英文 README、架构图、安全/可观测/数据库文档、ADR、贡献与安全说明（⚠ 待 maken 确认）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W10 | 1.5 天 | T54 | `main` |

## 目标
一个新同事只看文档就能明白：这是什么、怎么装、安全上做了什么、AI 为什么不会乱写账、数据库怎么选。文档只描述**已实现**的功能。

## 背景
- 实施方案 8 W10 第 2 条。
- 仓库现状：无 `docs/adr/`、无 `README.zh-CN.md`；已有 `docs/audit.md` 等；W5–W9 期间新建了 `docs/security.md`、`docs/observability.md`、`docs/agent.md`、`docs/vouchers.md`、`docs/mcp.md`、`docs/deploy.md`、`docs/install.md`。
- 不发布：文档里**不写**「pip install crosserp」「GHCR 镜像」等未提供的方式。

## 范围
- `README.md`（英文）与 `README.zh-CN.md`（中文）：一句话介绍、红线四条、功能清单（只列已实现）、安装（本地 wheel / Docker）、5 分钟上手、mermaid 架构图（导入 → 对账 → 利润 → 异常 → 凭证 → 审批 → 写出；AI 只读旁路）、截图/GIF 位（GIF 由 maken 录制）。**注意：`README.md` 中「任务列表」等已有段落保留，只增改介绍部分。**
- `docs/security.md`（权限矩阵、会话、CSRF、锁定、审计双链、token、脱敏、注入防护）、`docs/observability.md`、`docs/database.md`（三库差异、授权脚本、备份命令）。
- `docs/adr/0001-single-write-path.md`、`0002-llm-never-computes-money.md`、`0003-hash-chained-audit.md`、`0004-three-databases.md`（背景/决定/后果，引用对应任务号）。
- `CONTRIBUTING.md`（直接在 main 提交、提交信息带任务号、测试不过不提交、不删测试）、`SECURITY.md`（漏洞报告方式：私下联系 maken，联系方式由 maken 填，⚠ Q2）。
- 文档链接检查脚本（离线，检查仓库内相对链接存在）。
- 提交：`main`，`docs: add bilingual readme, adr and security docs (T55)`；不发布。

## 不做
- 不建文档网站；不翻译所有 docs（只 README 双语）。

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `python scripts/check_doc_links.py` | 0 个坏链接 |
| `uv run pytest -q` | 全过（文档改动不影响） |
| 人工自查：README 中每个功能都能对应到一个已完成任务号 | 完成记录列出对照表 |

## maken 人工验收清单
- [ ] 用屏幕录制工具录一段 30 秒内的 GIF（登录 → 看异常 → 问 AI），放到 `docs/assets/demo.gif`。
- [ ] 读一遍 `README.zh-CN.md`：有没有看不懂、或写了但其实没做的功能？
- [ ] 在 `SECURITY.md` 填上你愿意公开的联系方式（或写「内部使用，联系 maken」）。

## 问题
- Q1 按推荐默认：版本号改为 `0.5.0`，只改文件，不打 tag、不发布。
- Q2 按任务允许的安全占位：写“内部使用，联系 maken”，不编造公开联系方式。

## 完成记录
- 完成内容：新增英文/中文 README、架构图、安全/可观测/数据库补充、4 份 ADR、贡献指南、安全说明和离线文档链接检查脚本；版本号改为 0.5.0，不打 tag、不发布。
- 文档功能对照：导入/对账/利润/异常（T08–T24）；审批和唯一写出口（T27–T41）；AI 只读、脱敏、调用记录、MCP、预算（T42–T49）；评测与部署（T50–T52）；安装计时与质量门槛（T53–T54）。
- 安全联系方式按任务允许的占位写为“内部使用，联系 maken”，没有编造个人邮箱或电话。
- 验证：`python scripts/check_doc_links.py` 输出“文档相对链接完整”；README 版本冒烟测试 1 passed；ruff、mypy、pre-commit 通过。
- Windows GIF 录制和 Windows 实机安装由 maken 人工验收补充。
