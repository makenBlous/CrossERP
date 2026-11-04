# AGENTS.md 修改段落（W5–W10）

> 说明：AGENTS.md 已经写了「直接在 main 上提交、不建分支」（§6 第 3、8 条），这部分不用改。
> **必须加**的是第 A 部分「v1.0 前不发布」。第 B 部分是 AGENTS.md 与 W5+ 任务冲突的地方，不改的话代理按 AGENTS.md 开头（第 4 行）「冲突时停下来问 maken」的规则会卡住，每处都标了 ⚠ 待 maken 确认。
> 每段都写了「放在哪里」和「原文 → 新文」；没列出的内容一字不改。

---

## A. 必加：v1.0 前不发布

### A1. §5 红线末尾追加第 9 条
```markdown
9. **v1.0 前不发布**。不打 git tag、不发 PyPI、不推 GHCR / Docker Hub 等任何镜像仓库、不建 GitHub Release、不推到任何公开仓库。v0.5 只做「内部验收」（T56）。任务里如果出现发布动作，跳过并在「问题」一节写明。
```

### A2. §6 第 8 条最后一句
原文：
```
PR/发布等对外动作按 maken 的明确要求执行。
```
新文：
```
不开 PR；发布类动作 v1.0 前一律不做（见红线 9）。测试没全过不提交。
```

### A3. §8 完成定义新增一行（放在最后一行之前）
```markdown
- [ ] 没有打 tag、没有发布包或镜像、没有建 Release（`git tag --list` 与开始前一致）。
```

---

## B. 可选但建议：与 W5+ 冲突的地方（⚠ 待 maken 确认）

### B1. §1「当前阶段」⚠
原文第 21–25 行（从「**当前阶段：v0.1**」到 W4 那一段结束）之后**追加**（不删原文，原文作为历史）：
```markdown
**W5–W10（T32–T56，v0.5 内部验收）**：多用户登录与 5 个角色（W5）、凭证与金蝶/通用 Excel 写出（W6）、AI 只读问答（W7）、MCP / 监控 / 预算（W8）、评测与 Docker 部署（W9）、质量门槛与文档（W10）。仍然**不做**：任何平台 API 拉数、ERPNext 推送、写账类 AI 工具、任何发布。
**以任务文件为准**：上面「v0.1 不做」的条目，对 T32 起的任务不再适用。
```
选项：A 照上追加（推荐）；B 改写 §1 只保留当前阶段。

### B2. §3 目录限制 ⚠
原文：
```
v0.5 才有的目录（vouchers/ approval/ ledger/ auth/ observability/ agent/ mcp_server/）**现在不要建**；例外：从 T27 起可以建 `approval/`，从 T28 起可以建 `ledger/`，其余仍不要建。
```
新文：
```
v0.5 目录按任务开放：`approval/`（T27）、`ledger/`（T28）、`auth/`（T32）、`vouchers/`（T39）、`agent/`（T42）、`observability/`（T44）、`mcp_server/`（T47）、`evals/`（T50）。没到对应任务前不要建。
另外 T33 新建 `src/crosserp/config.py`、`web/routes/`；T52 新建 `Dockerfile`、`docker-compose.yml`、`deploy/`；T55 新建 `docs/adr/`、`README.zh-CN.md`、`CONTRIBUTING.md`、`SECURITY.md`。
```

### B3. §2 技术栈「以后（v0.5+，现在别装）」一行 ⚠
原文：
```
| 以后（v0.5+，现在别装） | PydanticAI 2.64、官方 `mcp` 2.3、opentelemetry-sdk 1.45、argon2-cffi 25.1 | — |
```
新文：
```
| v0.5 按任务加入（每个都要 maken 在对应任务 Q 里同意） | argon2-cffi 25.1（T32）、python-multipart（T33）、pydantic-ai(-slim) 2.66（T42，2026-11-04 PyPI 最新）、opentelemetry-sdk（T44，版本加入时以 PyPI 为准）、官方 `mcp` 2.3（T47）、pydantic-evals 2.66（T50，可选依赖组 `eval`） | 版本以加入当天 PyPI 为准，写进完成记录 |
```
注：PydanticAI 2.64 → 2.66、opentelemetry-sdk 1.45 当前是否最新「未核实」，以加入当天为准。

### B4. §4 mypy 范围 ⚠
原文：
```
`mypy --strict` 覆盖 `core db recon profit issues audit connectors`（建了 `approval/`、`ledger/` 之后也加进去）。
```
新文：
```
`mypy --strict` 覆盖 `core db recon profit issues audit connectors approval ledger`，以及之后新建的 `auth vouchers agent observability mcp_server evals config web`（新建目录的任务里就加进去，T54 做总检查）。
```

### B5. §7 / §8 覆盖率门槛 ⚠
- §7 `--cov-fail-under=60` → T54 完成后改 `80`。
- §8 原文「覆盖率不低于门槛（v0.1 = 60%）」→「覆盖率不低于门槛（v0.1 = 60%；T54 起 = 80%，见 T54 Q1）」。

### B6. §8「main 上的提交已通过 CI」⚠
原文：
```
- [ ] CHANGELOG、docs、任务状态已更新；`main` 上的提交已通过 CI。
```
新文（与 T51 Q1「仓库可见性」联动）：
```
- [ ] CHANGELOG、docs、任务状态已更新；本地按 `.github/workflows/ci.yml` 的命令全部跑过。远程 CI 能跑时附运行链接，不能跑时写「远程 CI 未核实」。
```

### B7. §9 提交信息 ⚠
- scope 列表追加：`auth` `approval` `ledger` `vouchers` `agent` `observability` `mcp` `evals` `deploy` `docs`。
- 原文最后一句「一个提交一件事；PR 标题同格式；PR 描述包含：…」改为：
```
一个提交一件事；不开 PR。原本写在 PR 描述里的内容（做了什么、如何验收、没做什么、未决问题）写进任务文件「完成记录」。
```
- §6 第 5 条、§4 最后一条、§11「在 PR 里逐条说明原因」中的「PR」同样改为「完成记录」。

### B8. §5 红线 2、3 的版本说明 ⚠（只追加，不改原句）
红线 2 末尾追加：
```
W6 起写出目标增加 `kingdee_xlsx`、`generic_xlsx`（T40、T41），仍只经 write_service 且需一次性审批 token；网页下载只读取已批准时生成的产物（T41 Q1）。
```
红线 3 末尾追加：
```
W7 起实现 AI：工具只走 `CROSSERP_AGENT_DATABASE_URL` 只读账号（PG/MySQL 未配置就拒绝启动 AI，不回退主账号）；AI 回答中的每个数字必须能在工具输出中找到，否则拦截（T43）。
```
红线 7 末尾追加：
```
登录/权限事件写 `security_event`（独立哈希链 `security`，T34），同样只追加。
```
