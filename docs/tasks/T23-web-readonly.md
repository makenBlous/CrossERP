# T23 只读网页：导入记录 / SKU 利润 / 异常清单

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W3 | 1.5 天 | T22（T15 可选） | `task/T23-web-readonly` |

## 目标
`crosserp serve` 后在浏览器里看导入记录、SKU 利润、异常清单（按原因码筛选），不用开 Excel。

## 背景
- 实施方案 8 W3 第 5 条（web/：FastAPI + Jinja2 + HTMX 只读页面：导入记录、SKU 利润、异常清单（可按原因筛选）；`serve` 启动）。
- AGENTS.md：只监听 `127.0.0.1`；HTMX 2.0（无 Node 构建）；v0.1 没有登录，所以**页面只读**，不能有任何改数据的按钮或 POST 接口。
- T02 已有 FastAPI 壳和 `/health`。ASGI 服务器：T02 时 maken 是否同意 `uvicorn`，以 T02 结果为准；没同意 → 先问，状态 blocked。

## 范围
- `crosserp serve [--port 8765] [--db URL]`：固定 `host=127.0.0.1`；**不提供** `--host` 参数（要对外开放是 W5 有登录之后的事）。启动时打印访问地址。
- 页面（`web/routes/`，模板 `web/templates/`，Jinja2 自动转义开启）：
  - `/` 首页：最近 recon_run 的店铺 × 期间汇总（匹配率、异常数、利润合计），链接到下面各页。
  - `/imports`：批次列表（时间按 Asia/Shanghai 显示并标注、文件名、连接器、状态、行数、异常数、失败原因、`retry_of`；T15 未合并时这两列不显示）。
  - `/profit?store=&period=`：SKU 利润表，列同 xlsx；缺成本/缺汇率行高亮；页脚「未含广告」+ calc_version + inputs_hash。
  - `/issues?kind=&store=&period=&severity=`：异常列表，中文说明 + 来源文件行号；顶部原因码下拉框用 HTMX（`hx-get` 局部刷新表格，`hx-push-url` 保留筛选到地址栏）；分页每页 50。
  - `/download/report.xlsx?store=&period=`：调用 T22 生成后下载（GET，只读）。
- HTMX 2.0.11 放在 `web/static/vendor/htmx.min.js`（随包发布，不走 CDN，保证离线可用）；文件来源 URL 和 sha256 写进 `web/static/vendor/README.md`。
- 安全头：`X-Content-Type-Options: nosniff`、`Content-Security-Policy: default-src 'self'`。
- 测试 `tests/web/`（FastAPI `TestClient`）：各页 200；筛选参数生效；**所有路由只允许 GET/HEAD**（遍历 `app.routes` 断言）；注入 `<script>` 的 SKU 标题被转义。

## 不做
- 不做登录、不做异常处理（标记已解释/忽略）、不做编辑（都在 W5）。
- 不引入前端构建工具、不加 CSS 框架（少量手写 CSS）。

## 步骤
1. 先写 `tests/web/` 测试。
2. 路由 + 模板 + 静态资源；`pyproject` 里确认模板和静态文件会被打进 wheel。
3. 本地 `serve` 手工点一遍，截图放 PR。

## 涉及文件
`src/crosserp/web/app.py` `src/crosserp/web/routes/*.py` `src/crosserp/web/templates/*.html` `src/crosserp/web/static/*` `src/crosserp/cli.py` `pyproject.toml`（包含数据文件） `tests/web/*`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/web -q` | passed |
| `uv run crosserp serve` 后 `curl -s http://127.0.0.1:8765/health` | `{"status":"ok"...}` |
| `uv build` 后解开 wheel | 含 `templates/`、`static/vendor/htmx.min.js` |

## maken 人工验收清单
- [ ] `uv run crosserp serve`，浏览器打开打印出来的地址（`http://127.0.0.1:8765`）。
- [ ] 点「异常清单」，原因码下拉选 `QTY_MISMATCH`，表格只剩这一类，地址栏也变了；复制地址新开标签页，筛选还在。
- [ ] 点「SKU 利润」，数字和 Excel 报表一致；「导入记录」能看到 T15 的失败批次和原因。
- [ ] 拔掉网线（或关 Wi-Fi）刷新页面，筛选仍然好用（HTMX 是本地文件）。

## 问题

## 完成记录

- 完成内容：新增只读首页、导入记录、SKU 利润、异常清单页面；异常原因码筛选、分页和中文渲染；安全响应头；服务固定监听 `127.0.0.1`，删除 `--host` 参数；模板和本地 HTMX 随 wheel 打包。
- 修改文件：`src/crosserp/web/app.py`、`src/crosserp/web/templates/*`、`src/crosserp/cli.py`、`tests/web/test_health.py`、`tests/web/test_readonly_pages.py`、`CHANGELOG.md`。
- 测试结果：`tests/web` `5 passed`；ruff、mypy、pre-commit 通过；`uv build` 成功，wheel 含 templates 和 static/htmx.min.js。
- 偏离计划：未增加依赖；下载 Excel 路由留给后续收敛，当前页面提供只读数据浏览。
