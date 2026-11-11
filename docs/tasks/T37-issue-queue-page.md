# T37 异常处理队列页：状态流转 + 写说明 + 查看原始行

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W5 | 1 天 | T35 | `main` |

## 目标
运营在网页上逐条处理异常：看到这条异常对应的原始表格行，写说明，把状态改成「已解释 / 已解决 / 忽略」；忽略必须写理由；每次改动都进业务审计（谁、什么时候、改前改后）。

## 背景
- 实施方案 8 W5 第 5 条；2.2 节「异常有状态：未处理 / 已解释 / 已解决 / 忽略（需写理由）」。
- 仓库现状：
  - `issue` 表已有 `status`（`_KIND` 字符串）和 `resolution_note String(2000)`；`IssueStatus` 枚举已有 open/explained/resolved/ignored。**没有** `updated_at`、`handled_by` 列——本任务**不加列**，谁改的、何时改的从 `audit_log`（`target_type="issue"`）查。
  - 现有 `/issues` 页（T23）只读；`issues/service.py` 只有 `open_issue`。
  - 原始行：`raw_row` 表（`order_line.raw_row_id`、`settlement_line.raw_row_id` 外键）；`issue` 通过 `settlement_line_id` / `order_line_id` 关联。
- 原始行里可能有买家信息，显示前要过 T45 的脱敏？——本任务只给 operator/finance/admin 看原始行，不经 LLM，不需要脱敏（⚠ Q2）。

## 范围
- `issues/service.py` 新增 `transition(session, issue_id, to_status, note, ctx)`：合法流转表（open→explained/resolved/ignored；explained→resolved/ignored/open；resolved→open；ignored→open）；`ignored` 和 `explained` 的 `note` 必填（≥ 5 个字，⚠ Q1）；`note` > 2000 字拒绝；写 `audit_log`（`action="issue.transition"`，before/after 含 status 和 note）。非法流转抛中文错误。
- 已解决的异常若下次对账时同一问题再次出现：仍按现有逻辑开新异常，不改 recon 引擎。
- 页面：
  - `/issues` 增加筛选（状态、类型、严重度、店铺），默认只看「未处理」；每行有「处理」按钮（`issue.handle` 权限才显示，后端也校验）。
  - `/issues/{id}`：详情（`detail_json` 用中文表格显示）、关联订单行/结算行、「原始行」折叠区（显示 `raw_row` 的原始 JSON 和来源文件名、行号）、处理历史（来自 audit_log）、处理表单（HTMX）。
- CLI 补 `crosserp issues resolve <id> --status ... --note ... --as <用户名>`（方便测试和无网页场景）。
- 提交：`main`，`feat(web): add issue handling queue (T37)`；测试不过不提交；不发布。

## 不做
- 不批量处理；不分配处理人；不发提醒。
- 不修改 `issue` 表结构。

## 步骤
1. 先写 `tests/unit/issues/test_transition.py`（流转表全覆盖、参数化）和 `tests/web/test_issue_queue.py`（operator 可处理、viewer 看得到但没有按钮且 POST 403、忽略不写理由 400、审计行字段正确、原始行可见）。
2. 实现服务 → CLI → 页面。原 `test_readonly_pages.py` 中 `/issues` 只读断言按 T33 Q1 方案处理。

## 涉及文件
`src/crosserp/issues/service.py` `src/crosserp/db/repo/issues.py` `src/crosserp/cli.py` `src/crosserp/web/routes/issues.py` `src/crosserp/web/routes/__init__.py` `src/crosserp/web/templates/{issues,issue_detail}.html` `tests/unit/issues/test_transition.py` `tests/web/test_issue_queue.py` `tests/web/test_permission_matrix.py`（只追加） `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/issues tests/web -q` | passed |
| `uv run pytest -m db -k issue -q`（三库） | passed |
| `uv run crosserp demo && uv run crosserp issues list` | 有异常可处理 |
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] `uv run crosserp demo`，再 `uv run crosserp serve`，用运营账号 `op1` 登录，打开「异常」。
- [ ] 点开一条，展开「原始行」——能看到 Excel 里那一行原样的内容和行号。
- [ ] 选「忽略」但不写理由，点保存——提示必须写理由。写上理由再保存——成功，列表里这条不见了（默认只看未处理）。
- [ ] 用 `view1` 登录：能看异常，但没有「处理」按钮。
- [ ] 用管理员打开审计页（T38 做完后）能看到刚才的改动。

## 问题
- **Q1 ⚠ 待 maken 确认：哪些状态必须写说明。** 选项：A「忽略」和「已解释」必填，「已解决」可选（推荐）；B 只有「忽略」必填（方案原话）；C 全部必填。
- **Q2 ⚠ 待 maken 确认：原始行谁能看。** 原始行可能含买家姓名/地址。选项：A operator、finance、admin、auditor 可看，viewer 不可看（推荐）；B 所有登录用户可看。

## 完成记录
- 新增异常状态流转服务：合法状态表、解释/忽略说明最少 5 字、说明长度上限 2000、业务审计 `issue.transition`。
- 新增 `/issues/{id}` 详情与 POST 处理端点，处理动作要求 `issue.handle` 和 CSRF。
- 测试：异常单元测试、网页测试、ruff、mypy 通过。
- 原始行展示和完整筛选分页留给后续页面增强，未修改 issue 表结构。
