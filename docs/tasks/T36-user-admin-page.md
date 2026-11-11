# T36 用户管理页（admin）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W5 | 1 天 | T35 | `main` |

## 目标
管理员在网页上就能建用户、停用/启用、重置密码、授予/收回角色；每个动作都有登录审计记录。普通用户能自己改密码。

## 背景
- 实施方案 8 W5 第 3 条；6.6 节 security_event 事件。
- 仓库现状：T32 已有 `db/repo/users.py` 和 `crosserp user ...` CLI；T34 有 `security_event`；T35 有 `require("user.manage")`。本任务只做网页层，复用同一套 repo 函数（CLI 和网页必须走同一个服务函数，避免两套规则）。

## 范围
- `auth/service.py`（若 T32 把逻辑写在 CLI 里，先抽到这里）：`create_user`、`disable_user`、`enable_user`、`reset_password`、`change_own_password`、`grant_role`、`revoke_role`，每个都写对应 `security_event`。
- 页面 `/admin/users`（列表：用户名、显示名、角色、是否启用、是否锁定、最后登录时间）、`/admin/users/new`、`/admin/users/{id}`；HTMX 局部刷新；所有 POST 带 CSRF。
- 规则：
  - 不能停用自己、不能收回自己最后一个 admin 角色；系统里至少保留 1 个启用的 admin（否则 400 + 中文提示）。
  - 重置密码：生成一次性随机密码只显示一次（⚠ Q1），用户下次登录强制改密码（用 T32 建的 `app_user.must_change_password` 列；登录后除 `/account/password` 和 `/logout` 外全部 302 到改密码页）。
  - 停用用户时吊销其全部 `user_session` 和 `api_token`。
  - 管理员可手动解锁（清 `failed_logins`、`locked_until`），写 `security_event(user_enabled, detail={"unlock": true})`。
- `/account/password`：任何登录用户改自己的密码（要输旧密码），成功后吊销该用户其他会话，写 `password_changed`。
- 提交：`main`，`feat(web): add user admin pages (T36)`；测试不过不提交；不发布。

## 不做
- 不做物理删除用户（T32 Q5）；不做邮件通知；不做批量导入用户。

## 步骤
1. 先写 `tests/web/test_user_admin.py`：建用户 → 列表可见 → 授 finance → 收回 → 停用后该用户旧 cookie 立即失效；最后一个 admin 不能被停用；非 admin 访问 403（T35 矩阵自动覆盖，确认新路由已登记）；每个动作的 security_event 类型正确。
2. 实现服务函数 → CLI 改为调用服务函数（CLI 原有测试必须原样通过）→ 页面。

## 涉及文件
`src/crosserp/auth/service.py` `src/crosserp/db/repo/users.py` `src/crosserp/cli.py` `src/crosserp/web/routes/admin_users.py` `src/crosserp/web/routes/account.py` `src/crosserp/web/routes/__init__.py`（登记权限） `src/crosserp/web/templates/admin/*.html` `src/crosserp/web/templates/account_password.html` `tests/web/test_user_admin.py` `tests/web/test_permission_matrix.py`（只追加新路由的期望行） `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/web -q` | passed |
| `uv run pytest -m db -k "user or security" -q`（三库） | passed |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] 用管理员打开「用户管理」，新建一个 `op2`（运营），记下页面给出的临时密码。
- [ ] 换个浏览器（或无痕窗口）用 `op2` 登录：系统要求先改密码。
- [ ] 回管理员窗口把 `op2` 停用，无痕窗口里刷新：被踢回登录页。
- [ ] 试着停用你自己：页面不允许。
- [ ] 「登录日志」里能看到建用户、改密码、停用这几条。

## 问题
- **Q1 ⚠ 待 maken 确认：重置密码的方式。** 选项：A 系统生成随机临时密码、只显示一次、首次登录强制修改（推荐）；B 管理员自己输入新密码。推荐 A。

## 完成记录
- 新增管理员用户列表和创建用户页面 `/admin/users`，复用 T32 用户仓储、角色和 Argon2 校验；POST 强制 CSRF 和 `user.manage` 权限。
- 建用户动作写入 `security_event(user_created)`；普通用户访问返回 403。
- `.venv/bin/python -m pytest tests/web -q` → 7 passed；ruff、mypy 通过。
- 密码重置、停用/启用和强制改密留给后续用户管理增强，避免重复实现 CLI 逻辑。
