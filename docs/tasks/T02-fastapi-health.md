# T02 FastAPI 最小服务：hello 页 + /health

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W1 | 0.5 天 | T01 | `task/T02-fastapi-health` |

## 目标
`crosserp serve` 能启动 B/S 服务，浏览器打开 `http://127.0.0.1:8000/` 看到「CrossERP 运行中」，`/health` 返回 JSON，供以后 Docker/安装脚本做健康检查。

## 背景
- 实施方案 2.4（B/S 架构，单机试用 `serve` 监听 127.0.0.1:8000）、3（FastAPI + Jinja2 + HTMX，无 Node 构建）。
- 实施方案 W1 写了「不要实现任何 AI 或网页功能」；本任务只做壳和健康检查，**不做任何业务页面**，与其不冲突（推断，若 maken 不同意可推到 W3）。

## 范围
- `src/crosserp/web/app.py`：`create_app() -> FastAPI` 工厂函数。
- `GET /` 用 Jinja2 模板 `web/templates/index.html` 渲染一行中文「CrossERP 运行中」+ 版本号。
- `GET /health` 返回 `{"status": "ok", "version": "<__version__>"}`；T04 完成后再加 `"db": "ok"|"error"`（本任务先不加）。
- `crosserp serve [--host 127.0.0.1] [--port 8000]`，默认只监听 127.0.0.1；`--host 0.0.0.0` 时打印中文警告「对外开放前请配置 HTTPS 和登录（v0.5）」。
- 把 uvicorn 加为依赖（FastAPI 运行需要；实施方案未单独列出，PR 中说明）。
- `web/static/` 放置 htmx 2.0.x 的 `htmx.min.js`（从官方 npm 包下载的 2.0.11 版本，写明来源 URL 和 sha256 到 `web/static/README.md`）；页面引用它，但本任务不用它做交互。

## 不做
- 不做登录、导入页、报表页、API 文档定制。不引入 Node/npm 构建。

## 步骤
1. `uv add uvicorn`。
2. 写 `create_app()`，挂 `StaticFiles` 和 `Jinja2Templates`（模板路径用 `importlib.resources` 或 `Path(__file__).parent`，保证打包后可用）。
3. CLI `serve` 子命令调用 `uvicorn.run(create_app(), host=..., port=...)`。
4. 确认 wheel 打包包含 templates/static（`pyproject.toml` 里配置包数据，`uv build` 后用 `unzip -l` 检查）。
5. 测试 `tests/web/test_health.py`：TestClient 请求 `/health` 返回 200 且 JSON 正确；请求 `/` 返回 200 且包含「CrossERP」。

## 涉及文件
`src/crosserp/web/app.py` `src/crosserp/web/templates/index.html` `src/crosserp/web/static/htmx.min.js` `src/crosserp/web/static/README.md` `src/crosserp/cli.py` `pyproject.toml` `uv.lock` `tests/web/test_health.py` `CHANGELOG.md`

## 验收标准
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/web -q` | 全部 passed |
| `uv run crosserp serve` 后另开终端 `curl http://127.0.0.1:8000/health` | `{"status":"ok","version":"0.0.1"}` |
| `uv build && python -m zipfile -l dist/*.whl` | 列表中有 `crosserp/web/templates/index.html` 和 `htmx.min.js` |
| `uv run ruff check . && uv run mypy` | 无错误 |

## maken 人工验收清单
- [ ] 运行 `uv run crosserp serve`，看到服务启动的提示。
- [ ] 浏览器打开 http://127.0.0.1:8000/ ，看到「CrossERP 运行中」。
- [ ] 浏览器打开 http://127.0.0.1:8000/health ，看到 `"status":"ok"`。
- [ ] 按 Ctrl+C 能正常停止。

## 问题

## 完成记录
