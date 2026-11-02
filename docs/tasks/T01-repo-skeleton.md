# T01 仓库骨架：uv + pyproject + 规范工具

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W1 | 0.5 天 | 无 | `task/T01-repo-skeleton` |

## 目标
得到一个能 `uv sync`、`uv run pytest`、`uv run ruff check`、`uv run mypy` 全部通过的空 Python 包 `crosserp`，以后所有任务都在它上面加东西。

## 背景
- 实施方案 3（技术栈）、7.1（目录）、7.2（规范）、8 W1 第 1 条。
- 改名：`agent_erp` → `crosserp`（见 AGENTS.md 第 0 节）。

## 范围
- `uv init --package` 风格的 `src/crosserp/` 布局，`requires-python = ">=3.12"`，`.python-version` 写 `3.14`。
- 依赖：`fastapi`, `jinja2`, `sqlalchemy>=2.1`, `alembic`, `pydantic>=2.14`, `typer`, `python-calamine`, `openpyxl`, `pyyaml`（connector 映射用；pyyaml 实施方案未列出，若不同意请改用其他方式——**先问 maken**）。
- optional-dependencies：`mysql = ["pymysql"]`，`postgres = ["psycopg[binary]"]`。
- dev 依赖组（`[dependency-groups] dev`）：`pytest`, `pytest-cov`, `hypothesis`, `ruff`, `mypy`, `pre-commit`, `httpx`（FastAPI TestClient 需要）。
- 下限版本按 AGENTS.md 第 2 节写（如 `fastapi>=0.162`），不要锁死上限。
- CLI 入口：`[project.scripts] crosserp = "crosserp.cli:app"`，`crosserp --version` 打印版本。
- `ruff`、`mypy`、`pytest` 配置都写在 `pyproject.toml`；pytest 注册 marker `db`、`slow`。
- 仓库文件：`LICENSE`（Apache-2.0 全文）、`NOTICE`、`README.md`（3 行占位）、`CHANGELOG.md`（Keep a Changelog 格式，含 `## [Unreleased]`）、`.gitignore`（Python + `.env` + `samples/real_anonymized/` + `*.db`）、`.env.example`（只有 `CROSSERP_DATABASE_URL=` 一行和注释）、`.pre-commit-config.yaml`（ruff-format、ruff、mypy 用 local hook 走 `uv run`）。
- 一个冒烟测试 `tests/unit/test_smoke.py`：`import crosserp` 且 `crosserp.__version__ == "0.0.1"`。

## 不做
- 不写任何业务代码、数据库代码、网页。不建 v0.5 目录。

## 步骤
1. `uv init --package --name crosserp --python 3.14 .`（或手写同等结构），删掉生成的 hello 示例代码。
2. 用 `uv add` / `uv add --optional` / `uv add --dev` 加依赖，生成 `uv.lock`。
3. 写 `src/crosserp/__init__.py`（`__version__ = "0.0.1"`）和 `src/crosserp/cli.py`（Typer app，`--version` 回调）。
4. 在 `pyproject.toml` 加：
   - `[tool.ruff]` `line-length = 100`，`target-version = "py312"`，`lint.select = ["E","F","I","B","UP","SIM","RUF"]`
   - `[tool.mypy]` `strict = true`，`packages = ["crosserp"]`，`mypy_path = "src"`
   - `[tool.pytest.ini_options]` `testpaths = ["tests"]`，`addopts = "-ra"`，markers
5. 建空目录占位（含 `__init__.py`）：`core db connectors recon profit issues audit web`。
6. 写 LICENSE/NOTICE/README/CHANGELOG/.gitignore/.env.example/.pre-commit-config.yaml。
7. 跑验收命令。

## 涉及文件
`pyproject.toml` `uv.lock` `.python-version` `src/crosserp/**/__init__.py` `src/crosserp/cli.py` `tests/unit/test_smoke.py` `LICENSE` `NOTICE` `README.md` `CHANGELOG.md` `.gitignore` `.env.example` `.pre-commit-config.yaml`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv sync --all-extras` | 退出码 0 |
| `uv run crosserp --version` | 输出 `0.0.1` |
| `uv run pytest` | 1 passed |
| `uv run ruff format --check . && uv run ruff check .` | 无错误 |
| `uv run mypy` | `Success: no issues found` |
| `git check-ignore samples/real_anonymized/x.csv` | 输出该路径（说明已忽略） |

## maken 人工验收清单
- [ ] 在 `D:\make\write\work\CrossERP` 打开 PowerShell，运行 `uv sync --all-extras`，没有红字报错。
- [ ] 运行 `uv run crosserp --version`，看到 `0.0.1`。
- [ ] 运行 `uv run pytest`，最后一行是绿色的 `1 passed`。
- [ ] 打开 `LICENSE`，第一行写着 Apache License。
- [ ] 打开 `.gitignore`，能找到 `samples/real_anonymized/` 和 `.env`。
- [ ] 确认是否同意加 `pyyaml` 依赖（代理会在 PR 里问）。

## 问题
- maken 已同意加 `pyyaml`。已写入 `pyyaml>=6.0.3`（PyPI 当前稳定版 6.0.3，2026-10-03 仍是最新；只写下限）。理由：T12 列映射要用 YAML。
- 版权人按 maken 指定写 `cimi`（`NOTICE` 与 `LICENSE` 附录）。
- 本机 `uv` 仍是 0.8.2，没有升级，也没有改 PATH。项目虚拟环境 `D:\make\write\work\CrossERP\.venv\Scripts\python.exe` 已核对为 Python 3.14.0b4。验收命令都在这个环境上跑过。
- `uv init` 写的构建后端是 `uv_build>=0.8.2,<0.9.0`。当前环境能构建。以后若换成 uv 0.13，这个上限可能要放宽。本次没有改它。
- `ruff format --check .` 会改写 `docs/plan/实施方案.md` 里的代码块。已在 `[tool.ruff]` 加 `extend-exclude = ["docs"]`，没有改实施方案。

## 完成记录
分支：`task/T01-repo-skeleton`。没有 remote，未推送，未开 PR。

2026-11-02 在 `D:\make\write\work\CrossERP` 实际运行（解释器 Python 3.14.0b4）：

| 命令 | 结果 |
|---|---|
| `uv sync --all-extras` | 退出码 0。`Audited 59 packages` |
| `uv run crosserp --version` | 退出码 0。输出 `0.0.1` |
| `uv run pytest` | 退出码 0。`1 passed` |
| `uv run ruff format --check .` | 退出码 0。`15 files already formatted` |
| `uv run ruff check .` | 退出码 0。`All checks passed!` |
| `uv run mypy` | 退出码 0。`Success: no issues found in 10 source files` |
| `git check-ignore samples/real_anonymized/x.csv` | 退出码 0。输出 `samples/real_anonymized/x.csv` |
| `uv run pytest --cov=crosserp --cov-fail-under=60` | 退出码 0。`Required test coverage of 60% reached. Total coverage: 100.00%`，`1 passed` |
| `uv run pre-commit run --all-files` | 退出码 0。`ruff-format`、`ruff`、`mypy` 均为 Passed |
