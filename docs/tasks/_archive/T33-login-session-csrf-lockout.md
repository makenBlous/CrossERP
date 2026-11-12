# T33 网页登录 / 登出 / 会话 / CSRF / 登录锁定 + `config.py`（⚠ 待 maken 确认）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W5 | 1.5 天 | T32 | `main` |

## 目标
打开网页先要登录；登录后 cookie 安全（HttpOnly、SameSite=Lax），所有会改数据的请求都要带 CSRF 令牌；连续输错 5 次密码锁 15 分钟；`serve` 可以改监听地址，但改成非本机地址时会大声提醒必须放在 HTTPS 反向代理后面。

## 背景
- 实施方案 8 W5 第 1 条；10 节风险表「多用户 = 更大攻击面」。
- 仓库现状：`web/app.py` 是单文件、只有 GET 路由（`/` `/health` `/imports` `/profit` `/issues`），有安全响应头中间件；T23 **删掉了** `serve --host`，固定 `127.0.0.1`。
- `tests/web/test_readonly_pages.py` 断言「所有路由只允许 GET/HEAD」。W5 起必须有 POST（登录、审批），这个断言会失败。红线：不删、不弱化已有测试——见 Q1。
- T31 任务写了 `config` 的 `audit.retention`，但仓库里**没有** `src/crosserp/config.py`（grep 无 `retention`）——属于 T31 遗留，本任务一并补上。
- FastAPI 读取表单需要 `python-multipart`（官方文档：https://fastapi.tiangolo.com/tutorial/request-forms/ ）；当前 `uv.lock` 没有它（2026-11-04 查快照）。

## 范围
- `src/crosserp/config.py`：`Settings`（Pydantic）读取顺序：环境变量 `CROSSERP_*` > `~/.crosserp/config.toml`（标准库 `tomllib`）> 默认值。字段：`auth.max_failed_logins=5`、`auth.lockout_minutes=15`、`auth.session_hours=12`（⚠ Q3）、`audit.retention.business="never"`、`audit.retention.security_days=180`（估算，T34 用）。`.env.example` 增加对应项。
- 拆分路由：`web/app.py` 只保留 `create_app` 装配；新增 `web/routes/{pages,auth}.py`、`web/deps.py`（`current_user`、`require_login`）、`web/csrf.py`。
- 登录：`GET/POST /login`、`POST /logout`；成功后生成 32 字节随机 session token（`secrets.token_urlsafe`），库里只存 sha256；cookie `crosserp_session`：HttpOnly、SameSite=Lax、Path=/、`Secure` 在 `CROSSERP_COOKIE_SECURE=1` 或请求为 https 时打开。登录成功轮换 session id（防会话固定）。
- 会话：过期或吊销 → 302 到 `/login?next=...`（HTML）或 401（`Accept: application/json` / HTMX `HX-Request`）；`next` 只允许站内相对路径。
- CSRF：每个会话一个 CSRF token（同步令牌模式），模板里 `<input type=hidden name=csrf_token>`，HTMX 用 `hx-headers` 发 `X-CSRF-Token`；所有非 GET/HEAD 请求校验，失败 403。`/login` 的 POST 用登录前临时 token（cookie + 表单双提交）。
- 锁定：`failed_logins` 达到上限 → `locked_until = now + 15 分钟`；锁定期间即使密码正确也拒绝，提示「账号已锁定，请 X 分钟后再试」（中文）；成功登录清零。不存在的用户名也走相同耗时（防止用户名探测，推断，用固定假哈希 verify 一次）。
- `serve --host`（默认 `127.0.0.1`）：非 `127.0.0.1`/`localhost`/`::1` 时在终端打印醒目中文警告「必须放在 HTTPS 反向代理后面，并设置 CROSSERP_COOKIE_SECURE=1」，并要求 `--i-understand-https` 才启动（⚠ Q2）。
- 所有现有页面（`/` `/imports` `/profit` `/issues`）改为需要登录；`/health` 和 `/static` 保持匿名。
- 本任务把 `record_security_event` 的调用点埋好（login_success / login_failed / logout / session_expired），实际写入在 T34 完成。
- 提交：`main`，`feat(web): add login, sessions, csrf and lockout (T33)`；测试不过不提交；不发布。

## 不做
- 不做角色权限（T35）、用户管理页（T36）；不做「记住我」、找回密码、二次验证。
- 不自己实现 HTTPS。

## 步骤
1. 先写测试 `tests/web/test_login.py`：未登录访问 `/issues` → 302；带 `HX-Request` → 401；正确登录 → 200 并带 HttpOnly + SameSite=Lax cookie；错 5 次 → 第 6 次即使密码对也被拒；把时间往后拨 15 分钟（注入时钟）→ 能登录；无 CSRF 的 POST → 403；登出后旧 cookie 无效；`next=https://evil.example` 被忽略。
2. 写 `tests/unit/test_config.py`：环境变量覆盖 toml，toml 覆盖默认值。
3. 处理 `tests/web/test_readonly_pages.py`（按 Q1 的决定），再实现代码。
4. `tests/web/test_serve_host.py`：`--host 0.0.0.0` 不带确认参数时退出码非 0 且打印警告。

## 涉及文件
`pyproject.toml` `uv.lock`（python-multipart） `src/crosserp/config.py` `.env.example` `src/crosserp/web/{app,deps,csrf}.py` `src/crosserp/web/routes/{__init__,pages,auth}.py` `src/crosserp/web/templates/{base,login}.html` 及现有 4 个模板（加导航与登出按钮） `src/crosserp/auth/sessions.py` `src/crosserp/db/repo/users.py` `src/crosserp/cli.py` `tests/web/` `tests/unit/test_config.py` `CHANGELOG.md` `docs/audit.md`（retention 配置说明）

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/web -q` | passed（含原有 `test_readonly_pages.py` 按 Q1 调整后仍在、仍通过） |
| `uv run pytest tests/unit/test_config.py -q` | passed |
| `uv run crosserp serve --host 0.0.0.0` | 打印 HTTPS 警告并退出码 ≠ 0 |
| 全量 pytest + 覆盖率 60、ruff、mypy、pre-commit | 全过 |

## maken 人工验收清单
- [ ] `uv run crosserp serve`，浏览器打开 http://127.0.0.1:8000/issues ——应该先跳到登录页。
- [ ] 用 T32 建的账号登录，能看到异常清单；右上角有「退出」。
- [ ] 退出后再按浏览器「后退」刷新——又回到登录页。
- [ ] 故意输错 5 次密码，第 6 次输对也进不去，提示要等多少分钟。
- [ ] `uv run crosserp serve --host 0.0.0.0`：终端出现「必须放在 HTTPS 反向代理后面」的提醒。

## 问题
已按 maken 决定对全部待确认项采用任务文件推荐：报表页保留 GET/HEAD 守卫并增加登录/CSRF 保护测试；非本机监听必须 `--i-understand-https`；会话 12 小时；加入 `python-multipart`。

## 完成记录
- 实现登录/登出、Argon2 密码验证、服务器端 `user_session`、HttpOnly/SameSite cookie、CSRF 双提交令牌、失败 5 次锁定 15 分钟；页面端点未登录返回 302，HX/JSON 返回 401，`/health` 和静态资源匿名。
- 新增 `config.py`，支持环境变量 > `~/.crosserp/config.toml` > 默认值；补充审计保留配置和 `.env.example`。
- `serve --host` 对外监听需要 `--i-understand-https` 并输出 HTTPS 警告；`python-multipart` 已锁定。
- 测试：`.venv/bin/python -m pytest tests/unit/test_config.py tests/web -q` → 8 passed；`.venv/bin/ruff check src tests`、`.venv/bin/mypy`、`.venv/bin/pre-commit run --all-files` 全部通过；`serve --host 0.0.0.0` 退出码 1 且输出 HTTPS 警告。
- 按推荐调整 `test_readonly_pages.py`：四个 T23 报表页继续只允许 GET/HEAD，同时新增登录/CSRF 测试；未删除测试。
- 全量 SQLite：`.venv/bin/python -m pytest --cov=crosserp --cov-fail-under=60` → `229 passed, 6 skipped`，覆盖率 `83.03%`。
