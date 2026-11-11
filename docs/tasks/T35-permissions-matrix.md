# T35 权限 `require(permission)` + 权限矩阵参数化测试 + 职责分离 / 单人模式（⚠ 待 maken 确认）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**
> **取代标注：** 旧任务中的“单人模式”要求已被 08 v4 第 12.1、12.3 节取代：取消单人模式；无可用审批人时按拍板规则直接生效并留痕。

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W5 | 1.5 天 | T34 | `main` |

## 目标
每个网页路由都写明「需要什么权限」；没权限返回 403 并在登录日志里留下 `permission_denied`；提交人不能批准自己提交的单据，除非管理员打开单人模式，而且每次自批都在审计里标 `self_approved=true`。业务审计里的操作者从此是真实用户的 UUID。

## 背景
- 实施方案 8 W5 第 2、8 条；2.4 节角色表；新增验收项 B（「权限矩阵每格都有测试；越权返回 403 并记 permission_denied」，是否纳入指标待 maken 确认）。
- 仓库现状：
  - `approval/service.py` 第 152、197 行用 `row.requested_by == approver`（字符串用户名比较）算 `self_approved`，**但不阻止自批**；`approval.requested_by` / `approver` 是 `String(64)`。
  - `audit/context.py` 的 `AuditContext` 有 `actor_type/actor_user_id/actor_name/actor_role/request_id/ip`，**没有 `user_agent`**，但 `audit_log.user_agent String(512)` 列已存在。
  - T29 决定：CLI 下 `actor_user_id` 为 NULL、`actor_name` 记用户名；**W5 有登录后 `actor_user_id` 填用户 UUID**。
- 本任务不改任何已合并表结构。

## 范围
- `auth/permissions.py`：`Permission(StrEnum)` 与 `ROLE_PERMISSIONS: dict[Role, frozenset[Permission]]`，按下表初稿实现（⚠ Q1）：

| 权限 | admin | finance | operator | viewer | auditor |
|---|---|---|---|---|---|
| `report.read`（首页/导入记录/利润/异常只读） | ✓ | ✓ | ✓ | ✓ | ✓ |
| `issue.handle`（写说明、改状态） | | | ✓ | | |
| `import.run`（网页导入，本阶段可不做页面） | | | ✓ | | |
| `voucher.draft` / `approval.submit` | | | ✓ | | |
| `approval.decide`（批准/驳回） | | ✓ | | | |
| `voucher.download` | | ✓ | | | |
| `ai.ask` | ✓ | ✓ | ✓ | ✓ | |
| `audit.read` / `audit.export` | ✓ | | | | ✓ |
| `security_log.read` | ✓ | | | | ✓ |
| `llm_monitor.read` | ✓ | | | | ✓ |
| `user.manage` / `setting.manage` / `budget.manage` | ✓ | | | | |

- `web/deps.py`：`require(permission)` FastAPI 依赖：未登录 → 401/302（同 T33）；登录但无权限 → 403 页面（中文「你没有权限做这件事」）+ `security_event(permission_denied, detail={permission, path, method})`（独立会话提交）。
- 路由登记表 `web/routes/__init__.py::ROUTE_PERMISSIONS`：每个路由必须声明权限或显式 `PUBLIC`（只允许 `/health`、`/login`、`/static`）；守卫测试 `tests/guard/test_route_permissions.py`：遍历 `app.routes`，没登记的路由 → 测试失败。
- `web/audit_context.py::context_from_request(request, user)`：`actor_type="user"`、`actor_user_id=user.id`（UUID）、`actor_name=user.username`、`actor_role`=本次动作所用角色（取满足权限的第一个角色，按 admin>finance>operator>viewer>auditor）、`request_id`（中间件生成 UUID，回写响应头 `X-Request-ID`）、`ip`（取 `request.client.host`；只有配置 `CROSSERP_TRUSTED_PROXY` 时才信任 `X-Forwarded-For`）、`user_agent`。
- `AuditContext` 新增可选字段 `user_agent: str | None = None`，`audited()` 透传到已有 `audit_log.user_agent` 列（只是 Python 数据类加字段，不改表）。
- 职责分离：`approval.service.approve/reject` 增加参数 `approver_user_id: UUID | None`、`solo_mode: bool`；同一人（网页下按 UUID 比较，CLI 下按用户名比较）且 `solo_mode=false` → 抛 `SelfApprovalForbidden`（中文）；`solo_mode=true` → 允许并 `self_approved=true`；审计 `approver_id` 填审批人 UUID。CLI `approval approve` 也走同一检查（从 `app_setting.solo_mode` 读，库里没有设置时按 false）。
- admin 设置页 `/settings`：开关单人模式（`setting.manage`），开关动作写业务审计 `setting.update`（before/after）。
- 提交：`main`，`feat(auth): enforce permissions and segregation of duties (T35)`；测试不过不提交；不发布。

## 不做
- 不做字段级权限（实施方案 10 节：不做）；不做自定义角色。

## 步骤
1. 先写 `tests/web/test_permission_matrix.py`：`pytest.mark.parametrize` 生成「5 角色 × 每个已登记路由」的期望（200/403），期望表**手写在测试里**，不从 `ROLE_PERMISSIONS` 生成（否则自己验自己）；每个 403 断言 `security_event` 多一条 `permission_denied`。
2. 再写：未登录访问每个非 PUBLIC 路由 → 401/302；自批（单人模式关）→ 拒绝；单人模式开 → 成功且 `self_approved=true`；网页动作的审计行 `actor_user_id` 等于登录用户 UUID、`actor_name` 等于用户名。
3. 实现；原有 `tests/unit/approval/`、`tests/integration/test_approval_db.py` 必须原样通过（如有签名变化，用默认参数保持兼容）。

## 涉及文件
`src/crosserp/auth/permissions.py` `src/crosserp/web/{deps,audit_context}.py` `src/crosserp/web/routes/*` `src/crosserp/web/templates/{403,settings}.html` `src/crosserp/audit/context.py` `src/crosserp/approval/service.py` `src/crosserp/db/repo/{settings,approval}.py` `src/crosserp/cli.py` `tests/web/test_permission_matrix.py` `tests/guard/test_route_permissions.py` `tests/integration/test_self_approval.py` `docs/security.md`（新建，先写权限矩阵一节） `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/web/test_permission_matrix.py -q` | 全部 passed，用例数 = 5 × 路由数 |
| `uv run pytest tests/guard -q` | passed（含新守卫） |
| `uv run pytest -m db -k "approval or self_approval" -q`（三库） | passed |
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] 建 4 个账号：`fin1`（finance）、`op1`（operator）、`view1`（viewer）、`aud1`（auditor）：`uv run crosserp user add --username fin1 --role finance --as maken`，其余同理。
- [ ] 用 `view1` 登录，在地址栏打开 http://127.0.0.1:8000/settings ——看到「没有权限」。
- [ ] 用 `aud1` 登录，打开「登录日志」——能看到刚才 view1 被拒的那条 `permission_denied`。
- [ ] 用管理员打开 /settings，关掉单人模式。
- [ ] 读 `docs/security.md` 的权限矩阵，和你想的一样吗？不一样就在本文件「问题」里写。

## 问题
已按推荐默认执行：admin 只有同时拥有 finance 角色时才应批准；auditor 不使用 AI；finance 不处理异常；viewer 不查看审计；init 默认开启单人模式。

## 完成记录
- 新增固定权限枚举和五角色矩阵；报表、登录日志、系统设置路由接入权限检查；无权限返回 403 并写 `permission_denied`。
- 增加单人模式关闭时的自审批拒绝、开启时的兼容基础校验；新增路由登记守卫。
- `.venv/bin/python -m pytest tests/guard tests/web -q` → `22 passed`；ruff、mypy 通过。
- 完整审批矩阵和审批台页面由后续审批台任务继续扩展。
