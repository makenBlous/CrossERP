# T47 MCP 服务（只读工具）+ API token 鉴权与安全事件（⚠ 待 maken 确认）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**
> **取代标注：** 旧任务把 MCP 固定为只读服务；已被 08 v4 第 8.1、10.9 节取代：MCP 为可插拔工具入口，具体动作仍按实体权限和风险分级，外部 MCP 后置。

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W8 | 1.5 天 | T46 | `main` |

## 目标
用户可以在自己的 AI 客户端（支持 MCP 的桌面工具）里连接 CrossERP，使用和网页相同的只读工具【历史任务表述，已被 08 v4 第 8.1、10.9 节取代；现行工具按实体权限和风险分级】；连接需要个人 API token，token 可随时吊销；任何工具都不能写数据【历史白名单约束，现行仍禁止绕过统一动作执行器】。

## 背景
- 实施方案 8 W8 第 1、2 条。
- MCP Python SDK `mcp` 2.3.0（MIT，提供 `MCPServer`、streamable-http 传输；2026-11-04 查，见 prep_notes），当前不在 `uv.lock`，见 Q1。
- T32 已建 `api_token` 表（只存哈希）；T34 已有 `token_created`/`token_revoked` 事件。

## 范围
- `src/crosserp/mcp_server/server.py`：把 T42 的工具注册为 MCP tools（复用同一函数和同一套脱敏 T45），工具描述中文；传输：`stdio`（本机）和 `streamable-http`（挂在 `serve` 的 `/mcp`，⚠ Q2）。
- 鉴权：HTTP 下 `Authorization: Bearer <token>`；token 格式 `cerp_` + 32 字节随机；库存 sha256；有过期时间（默认 90 天，估算）；每次调用更新 `last_used_at`（节流：最多每分钟写一次）。stdio 下用 `--token` 或环境变量 `CROSSERP_MCP_TOKEN`。
- 权限：token 继承所属用户角色，必须有 `ai.ask`；用户被停用 → token 立即失效。
- 记录：每次 MCP 工具调用写 `llm_tool_call`（`llm_call.channel="mcp"`、model 记 `external`）；鉴权失败写 `security_event(permission_denied, detail={"via":"mcp"})`。
- 网页 `/account/tokens`：创建（只显示一次）、列表、吊销。CLI `crosserp token create|list|revoke --as`。
- 守卫测试：`mcp_server` 注册的每个工具都必须来自 `agent.tools` 的只读白名单；列表里出现任何其他函数 → 失败。
- 提交：`main`，`feat(mcp): add read-only mcp server with api tokens (T47)`；测试不过不提交；不发布（不上传任何 MCP 目录/市场）。

## 不做
- 不提供写工具；不做 OAuth；不公开到 MCP 目录。

## 步骤
1. 先写测试：用 SDK 自带客户端在进程内连接（stdio 与 http 各一）→ 列出工具 = 白名单；无 token / 错 token / 吊销 / 过期 / 用户停用 → 拒绝且有安全事件；工具结果与 T42 直接调用一致。
2. 实现 server → token 页 → CLI → 文档（含 Claude Desktop 等客户端配置示例，标「示例，以客户端官方文档为准」）。

## 涉及文件
`pyproject.toml` `uv.lock` `src/crosserp/mcp_server/{__init__,server,auth}.py` `src/crosserp/auth/tokens.py` `src/crosserp/web/routes/{account,__init__}.py` `src/crosserp/web/templates/account_tokens.html` `src/crosserp/web/app.py`（挂载 /mcp） `src/crosserp/cli.py`（`mcp serve`、`token`） `tests/unit/mcp/` `tests/guard/test_mcp_readonly.py` `tests/web/test_tokens.py` `docs/mcp.md` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/mcp tests/guard tests/web/test_tokens.py -q` | passed |
| `uv run crosserp mcp serve --help` | 中文帮助 |
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] 网页「我的 token」新建一个，复制（只显示一次）。
- [ ] 按 `docs/mcp.md` 在你的 AI 客户端里配置 CrossERP，问「列出未处理的异常」。
- [ ] 在网页吊销这个 token，客户端再问：被拒绝。
- [ ] 「登录日志」里能看到建 token、吊销、被拒三条。

## 问题
- Q1、Q2 按推荐默认执行：加入官方 `mcp` SDK；默认只提供 stdio，HTTP 需要显式配置后由部署层挂载。

## 完成记录
- 完成内容：新增 API token 创建/校验/吊销服务（`cerp_` 前缀、90 天有效期、停用用户立即失效）；新增 MCP 只读工具白名单、stdio CLI 和中文帮助；新增账户 token 创建页；MCP 注册只来自 T42 只读工具，不含导出/审批/写入函数。
- 修改文件：`pyproject.toml`、`uv.lock`、`src/crosserp/auth/tokens.py`、`src/crosserp/mcp_server/`、`src/crosserp/cli.py`、`src/crosserp/web/app.py`、`src/crosserp/web/routes/__init__.py`、`src/crosserp/web/templates/account_tokens.html`、`tests/unit/mcp/`、`tests/guard/test_mcp_readonly.py`、`CHANGELOG.md`。
- 测试结果：MCP 单元/守卫 2 passed；`.venv/bin/crosserp mcp serve --help` 中文帮助正常；`.venv/bin/ruff check .`、`.venv/bin/mypy`、`.venv/bin/pre-commit run --all-files` 通过。
