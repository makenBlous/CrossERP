# docs/tasks/README.md 追加 / 修改内容（W5–W10，T32–T56）

> 本文件不是要放进仓库的新文件，而是「怎么改 `docs/tasks/README.md`」的说明。按 ①②③④⑤ 五处操作，其他内容一字不改。

## ① 状态表：改 T26 一行（只改「任务」和「状态」两格）
原行：
```
| T26 | [发布 v0.1.0（发布动作由 maken 操作）](T26-release-v01.md) | W3 | 0.5 天 | T25 | todo |
```
改为：
```
| T26 | [发布 v0.1.0（暂缓：v1.0 前不发布）](T26-release-v01.md) | W3 | 0.5 天 | T25 | 暂缓（v1.0 前不发布） |
```
同时在 `T26-release-v01.md` 头表把状态 `todo` 改为 `暂缓（v1.0 前不发布）`，文件其余内容不动。
（「暂缓」是新状态值，见 ④ 的状态说明补充。）

## ② 状态表：在 T31 一行之后追加
```
| T32 | [用户 / 角色 / 会话表 + argon2 + `init` 建第一个管理员（⚠ 待 maken 确认）](T32-auth-tables-init-admin.md) | W5 | 1.5 天 | T31（maken 同意开 W5） | todo |
| T33 | [网页登录 / 登出 / 会话 / CSRF / 登录锁定 + `config.py`（⚠ 待 maken 确认）](T33-login-session-csrf-lockout.md) | W5 | 1.5 天 | T32 | todo |
| T34 | [登录/权限审计 security_event：独立哈希链 + 登录日志页 + 导出（⚠ 待 maken 确认）](T34-security-event-chain.md) | W5 | 1 天 | T33 | todo |
| T35 | [权限 `require(permission)` + 权限矩阵参数化测试 + 职责分离 / 单人模式（⚠ 待 maken 确认）](T35-permissions-matrix.md) | W5 | 1.5 天 | T34 | todo |
| T36 | [用户管理页（admin）](T36-user-admin-page.md) | W5 | 1 天 | T35 | todo |
| T37 | [异常处理队列页：状态流转 + 写说明 + 查看原始行](T37-issue-queue-page.md) | W5 | 1 天 | T35 | todo |
| T38 | [审批台 + 审计页（改前改后对比、链状态）+ W5 验收证据](T38-approval-console-audit-page.md) | W5 | 1.5 天 | T36、T37 | todo |
| T39 | [凭证草稿：会计科目映射 `accounts.yaml` + `voucher` / `voucher_line` 表 + 借贷平衡（⚠ 待 maken 确认）](T39-voucher-model-accounts.md) | W6 | 2 天 | T38 | todo |
| T40 | [写出目标重构 + 金蝶导入模板 `kingdee_xlsx`（表头可配置，⚠ 待真实模板验证）](T40-ledger-kingdee-xlsx.md) | W6 | 1.5 天 | T39 | todo |
| T41 | [通用 Excel 目标 `generic_xlsx` + 网页「下载凭证」+ W6 验收证据（⚠ 待 maken 确认）](T41-generic-xlsx-download-w6.md) | W6 | 1.5 天 | T40 | todo |
| T42 | [AI 只读工具层 `agent/tools.py`（只读账号）+ 规则文档检索（⚠ 待 maken 确认）](T42-agent-readonly-tools.md) | W7 | 1.5 天 | T41 | todo |
| T43 | [AI 运行时：引用检查 + 数字核对 + `crosserp ask` + 提示词文件（⚠ 待 maken 确认）](T43-agent-runtime-ask.md) | W7 | 2 天 | T42 | todo |
| T44 | [AI 调用记录：OTel → 数据库（`llm_call` / `llm_tool_call` / `prompt_version`）+ 费用表（⚠ 待 maken 确认）](T44-llm-observability-tables.md) | W7 | 1.5 天 | T43 | todo |
| T45 | [发给模型前脱敏 + 提示注入防护 + AI 正文保留期（⚠ 待 maken 确认）](T45-redaction-injection-retention.md) | W7 | 1 天 | T44 | todo |
| T46 | [网页 AI 问答页：引用可点开到原始行 + 审计](T46-web-ask-page.md) | W7 | 1 天 | T45 | todo |
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
```

## ③ 替换这一句
原句：
```
W5 及以后的任务（登录与角色、凭证、AI 问答等）等 W4 验收后再拆。
```
替换为：
```
W5–W10（T32–T56）已按 T31 完成时（提交 57190c2）的仓库实际状态拆好，目标是 **v0.5 内部验收**（T56），不是发布。工作量（估算）：W5 约 9 天、W6 约 5 天、W7 约 7 天、W8 约 4 天、W9 约 4 天、W10 约 5 天，合计约 34 个代理工作日；按兼职节奏大概率顺延，以验收通过为准。

建议顺序：
- W5（登录与权限）：T32 → T33 → T34 → T35 → T36 / T37（可互换）→ T38。
- W6（凭证）：T39 → T40 → T41。
- W7（AI 问答）：T42 → T43 → T44 → T45 → T46。
- W8（MCP、监控、预算）：T47 → T48 → T49。
- W9（评测、部署）：T50 → T51 → T52。
- W10（v0.5 内部验收）：T53 → T54 → T55 → T56。

开 W5 的前提：T27–T31 目前是 `review`，T32 依赖 T31。maken 二选一：把 T27–T31 验收改为 `done`；或在 T32「问题」一节写「同意先开 W5」。

**v1.0 前不发布**：T32–T56 任何任务都不打 tag、不发 PyPI / GHCR / Docker Hub、不建 GitHub Release、不推到公开仓库。原计划的「W10 发布」改为「T56 v0.5 内部验收」。T26 暂缓，到 v1.0 再处理。
```

## ④ 「状态取值」一句后补一句
```
另有 `暂缓`：maken 决定推迟的任务（目前只有 T26），代理不做、也不算进依赖；依赖 T26 的任务视为不依赖它。
```

## ⑤ 「需要 maken 先拍板」表：T26 行改写，并在末尾追加
T26 行改为：
```
| T26 | 暂缓（v1.0 前不发布）；到 v1.0 时再定 PyPI 名字、trusted publisher、tag |
```
表末追加：
```
| T32 | 是否同意 T27–T31 未 done 时先开 W5；argon2-cffi 依赖；会话表名；密码最短长度；设置表；不物理删用户；demo 密码 |
| T33 | test_readonly_pages 断言怎么调整（不删测试）；非本机监听的门槛；会话时长；python-multipart 依赖 |
| T34 | 登录日志保留期；失败登录用户名怎么记；是否加 user_enabled 事件 |
| T35 | 权限矩阵 4 个争议格；单人模式默认值（开放问题 ⑦） |
| T36 | 重置密码方式 |
| T37 | 哪些状态必须写说明；原始行谁能看 |
| T39 | accounts.yaml 位置；凭证粒度；分录结构；舍入尾差 |
| T40 | 金蝶产品线（开放问题 ③）；待真实模板验证 |
| T41 | 网页一次性 token 用法；批准时生成哪些格式 |
| T42 | pydantic-ai 依赖；规则文档检索方式 |
| T43 | 默认模型供应商（开放问题 ②）；真实 key 怎么测；数字无来源是否重试 |
| T44 | opentelemetry-sdk 依赖；正文清理方式 |
| T45 | AI 正文保留天数；本地模型是否脱敏 |
| T47 | mcp 依赖；HTTP 方式是否默认开 |
| T48 | 谁能看问答全文 |
| T49 | 预算按金额还是 token；超额后 admin 是否豁免 |
| T50 | pydantic-evals 依赖；是否用裁判模型；20 题由 maken 审核 |
| T51 | 仓库可见性与 CI（与不发布冲突）；真实模型评测是否放 CI |
| T52 | 团队部署默认数据库（开放问题 ⑥）；反向代理示例 |
| T53 | 不上 PyPI 时从哪里安装 |
| T54 | 覆盖率门槛 |
| T55 | 版本号是否改 0.5.0（不打 tag）；SECURITY.md 联系方式 |
| T56 | 新增验收项 A–F 是否计入（开放问题 ⑧）；真实数据未核对能否有条件通过 |
```

（可选）任务模板里「涉及文件」一行的「PR 里说明原因」和「完成记录」的「PR 链接」与直接提交到 main 不一致，建议改为「完成记录里说明原因」「提交哈希」。⚠ 待 maken 确认。
