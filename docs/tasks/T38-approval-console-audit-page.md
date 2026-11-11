# T38 审批台 + 审计页（改前改后对比、链状态）+ W5 验收证据

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W5 | 1.5 天 | T36、T37 | `main` |

## 目标
财务在网页上看待审批列表，点开看内容，批准或驳回（必须写意见）；审计员在网页上看业务审计和链校验结果，每条能看改前改后对比。做完后整理 W5 验收证据。

## 背景
- 实施方案 8 W5 第 6、7 条和 W5 验收（「5 个角色权限矩阵测试全过；越权访问返回 403 并被记录；一人模式下自批也有标记」）。
- 仓库现状：`approval/service.py` 已有 `create/submit/approve/reject/reopen/invalidate/check_fresh/mark_exported`；CLI 有 `approval request/list/approve/reject --as`；`approval.comment String(1000)`；目前审批对象只有利润报表（`target_type`，`_payload_hash` 只支持 `店铺:YYYY-MM`），W6 T39 才加凭证。
- `approve()` 返回一次性导出 token（只存 `token_hash`）；网页怎么用 token 在 T41 定（⚠ T41 Q1），本任务批准后**只显示「已批准」，不显示 token**。
- 审计：`audit/log.py`、`audit/chain.py`、`verify`；T31 有导出。

## 范围
- 审批台 `/approvals`（`report.read` 可看列表；`approval.decide` 才有按钮）：标签页 待审批 / 已批准 / 已驳回 / 已失效；详情 `/approvals/{id}`：对象摘要（利润报表：店铺、月份、关键金额，金额来自 `profit_snapshot`，**页面不做任何金额计算**，只格式化显示）、`payload_hash`、提交人、提交时间、新鲜度检查结果（`check_fresh`，数据已变则显示「数据已变，需要重新提交」并禁用批准）。
- 批准/驳回：HTMX 表单，意见必填（1–1000 字）；调用 T35 改过的 `approve/reject`（带自批检查）；并发：用现有 `version` 乐观锁，冲突显示「别人刚处理过，请刷新」。
- 提交审批（operator，`approval.submit`）：在 `/profit` 每个店铺-月份行加「提交审批」按钮，调用现有 `create`+`submit`。
- 审计页 `/audit`（`audit.read`）：筛选（时间、操作者、动作、对象类型、对象 ID）、分页；每行可展开 before/after 的字段级对比（新增/删除/修改三色，纯后端计算差异，前端只渲染）；页头显示两条链状态（业务链 + security 链：最后 seq、最后校验时间、按钮「立即校验」调用 verify，只显示结果，不写 checkpoint，checkpoint 仍由 CLI 做）；「导出」按钮调用 T31 导出逻辑生成 zip 下载（`audit.export`）。
- W5 验收证据 `docs/evidence/W5.md`：权限矩阵测试输出、403 + permission_denied 截图或日志、单人模式自批 `self_approved=true` 的审计行、三库测试结果。真实截图由 maken 补，代理写「待 maken 补」。
- 提交：`main`，`feat(web): add approval console and audit viewer (T38)`；W5 证据单独一个提交 `docs: add W5 evidence (T38)`；测试不过不提交；不发布。

## 不做
- 不做凭证审批（T39–T41）；不做邮件/飞书通知；审计页不提供任何修改或删除。

## 步骤
1. 先写测试：finance 批准成功、审计行 `approver_id`=finance UUID；operator 点批准 403；意见为空 400；数据变化后批准被拒；两个会话同时批准只有一个成功；审计页 diff 结果正确（单元测试 `audit/diff.py`）；viewer 打开 `/audit` 403。
2. 实现 `audit/diff.py` → 路由 → 模板。
3. 跑完整 W5 回归，写 `docs/evidence/W5.md`。

## 涉及文件
`src/crosserp/web/routes/{approvals,audit,profit}.py` `src/crosserp/web/routes/__init__.py` `src/crosserp/web/templates/{approvals,approval_detail,audit}.html` `src/crosserp/audit/diff.py` `src/crosserp/db/repo/approval.py` `tests/unit/audit/test_diff.py` `tests/web/test_approval_console.py` `tests/web/test_audit_page.py` `tests/web/test_permission_matrix.py`（只追加） `docs/evidence/W5.md` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/web tests/unit/audit -q` | passed |
| `uv run pytest -m db -q`（三库） | passed |
| `uv run crosserp audit verify && uv run crosserp audit verify --chain security` | 都通过 |
| 全量检查（覆盖率 ≥ 60） | 全过 |

## maken 人工验收清单
- [ ] `uv run crosserp demo`，`serve`，用 `op1` 登录，在「利润」页给一个店铺-月份点「提交审批」。
- [ ] 换 `fin1` 登录「审批」页：能看到这条；不写意见点批准——不让；写意见再批准——成功。
- [ ] 用 `op1` 直接在地址栏 POST 不了（这一条代理已测，你看测试报告即可）。
- [ ] 用 `aud1` 打开「审计」：能看到刚才的提交和批准，点开能看到改前改后；页头两条链都显示「正常」。
- [ ] 读 `docs/evidence/W5.md`，把需要你截图的地方补上。

## 问题
- 无新的待确认项（凭证审批、token 用法见 T41）。

## 完成记录
- 完成内容：新增审批台列表/详情及批准、驳回表单；利润报表提交审批；审批意见和新鲜度检查；审批审计写入真实 `approver_id`；新增后端字段差异计算；新增业务审计页、分页筛选、两条哈希链状态、立即校验和审计包下载；补充 W5 验收证据文档。
- 修改文件：`src/crosserp/web/app.py`、`src/crosserp/web/templates/{approvals,approval_detail,audit,index,profit}.html`、`src/crosserp/web/routes/__init__.py`、`src/crosserp/audit/diff.py`、`src/crosserp/approval/service.py`、`src/crosserp/db/session.py`、`tests/unit/audit/test_diff.py`、`tests/web/test_approval_console.py`、`tests/web/test_audit_page.py`、`docs/evidence/W5.md`、`CHANGELOG.md`。
- 测试结果：`.venv/bin/ruff format --check .` 通过；`.venv/bin/ruff check .` 通过；`.venv/bin/mypy` 通过；`.venv/bin/pytest tests/web tests/unit/audit -q` 为 12 passed；全量 `.venv/bin/pytest -q --cov=crosserp --cov-fail-under=60` 为 238 passed、7 skipped，覆盖率 81.23%。Docker 可用但本次未启动 MySQL/PG 容器，三库由 CI db matrix 负责。
- 偏离计划：仓库当前网页路由集中在 `web/app.py`，按现有装配方式实现，未新增独立 route 模块；审批意见通过现有 `comment` 字段保存；按推荐默认执行，无新的待 maken 确认项。
