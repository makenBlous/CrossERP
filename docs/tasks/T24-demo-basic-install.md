# T24 `crosserp demo` + 基础安装（`uv tool install` 三系统可用）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W3 | 1 天 | T21, T23 | `task/T24-demo-install` |

## 目标
新用户在 Windows / macOS / Linux 上装好后，一条 `crosserp demo` 看到完整效果；不再需要手动设 `PYTHONPATH`。

## 背景
- 实施方案 8 W3 第 6 条（`demo` = init + 导入合成样本 + 对账 + 打开浏览器）、W3 验收「`uv tool install` + `demo` 在三系统可用」、指标 1 v0.1 档「基础能装」（≤15 分钟 ≤3 命令是 v0.5 指标，证据来自 W9 install-matrix）。
- maken 目前本地运行方式是设置 `$env:PYTHONPATH=...\src` 再用 `.venv\Scripts\python.exe -m crosserp.cli ...`。这说明 `crosserp` 命令在他的 .venv 里可能没有以可编辑方式安装好（推断，未核实原因）。本任务要让 `uv sync` 后 `uv run crosserp ...` 直接可用，并在 PR 里写清楚原因。

## 范围
- 开发环境：确认 `pyproject.toml` 的 `[project.scripts] crosserp = "crosserp.cli:app"` 和构建后端配置正确，`uv sync` 后 `uv run crosserp --help` 不设 PYTHONPATH 就能用；`python -m crosserp` 也可用（加 `__main__.py`）。在 Windows PowerShell 上实测。
- 合成样本随包发布：`src/crosserp/demo/samples/`（由 `scripts/gen_samples.py --out` 生成）；测试断言它和 `samples/synthetic/` 内容**逐字节相同**，防止两份不同步。`demo` 读包内样本（`importlib.resources`），不依赖仓库目录。
- `crosserp demo [--db URL] [--no-browser] [--check] [--port 8765]`：
  1. 默认使用**独立的演示库** `~/.crosserp/demo.db`（不碰用户正式库 `data.db`）；已存在 → 提示并重建（只删 demo.db）。
  2. init → 导入包内样本 → reconcile 2026-10 → profit → 打印汇总（匹配率、异常数、利润合计）。
  3. 默认启动 serve 并用 `webbrowser.open` 打开首页；`--no-browser` 不开浏览器。
  4. `--check`：不启动服务，只做 1–2 步并断言「匹配率 ≥95%、未匹配 100% 有原因、golden 一致」，通过退出码 0（给 CI 和 W9 install-matrix 用），打印耗时。
- CI：`ci.yml` 新增 job `install-smoke`（3 系统 × Python 3.12）：`uv build` → `uv tool install dist/*.whl` → `crosserp demo --check`；记录耗时到 job summary。
- README「快速开始」改为 3 条命令：安装 uv → `uv tool install crosserp`（发布前用 wheel 路径）→ `crosserp demo`。

## 不做
- 不做 Docker 镜像（v0.5）、不做安装包/exe。
- 不发布到 PyPI（T26）。

## 步骤
1. 先在干净目录复现 maken 的问题（`uv sync` 后直接 `uv run crosserp --help`），记录现象和原因。
2. 实现 `demo`、包内样本、`__main__.py`。
3. 写 `tests/integration/test_demo.py`（`--check --no-browser`，临时目录做 HOME）和 CI job。

## 涉及文件
`pyproject.toml` `src/crosserp/__main__.py` `src/crosserp/demo/*` `src/crosserp/cli.py` `scripts/gen_samples.py` `tests/integration/test_demo.py` `.github/workflows/ci.yml` `README.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| 新开终端、不设 PYTHONPATH：`uv sync && uv run crosserp --help` | 显示中文帮助 |
| `uv run crosserp demo --check` | 退出码 0，打印匹配率 ≥95%、golden 一致、耗时 |
| CI `install-smoke` 三系统 | 全绿 |
| 跑完 demo 后 `~/.crosserp/data.db` | 未被创建或修改 |

## maken 人工验收清单
- [ ] Windows 上新开 PowerShell（**不要**设 PYTHONPATH），`cd D:\make\write\work\CrossERP`，`uv sync`，`uv run crosserp --help`，能出帮助。
- [ ] `uv build`，然后 `uv tool install (Get-ChildItem dist\*.whl | Select-Object -First 1).FullName`，换到别的目录运行 `crosserp demo`，浏览器自动打开，看到首页。用手机计时，记下总耗时。
- [ ] 如有 Mac 或 Linux 机器，重复上一步（没有就以 CI `install-smoke` 为准，在完成记录里注明）。

## 问题

## 完成记录

- 完成内容：新增包内 `crosserp/demo/samples`、`crosserp demo --check/--no-browser`、`python -m crosserp`；demo 使用独立 `~/.crosserp/demo.db`，不碰正式库；新增三系统 wheel install-smoke CI；README 快速开始更新。
- 修改文件：`src/crosserp/demo/*`、`src/crosserp/__main__.py`、`src/crosserp/cli.py`、`scripts/gen_samples.py` 生成的包内样本、`.github/workflows/ci.yml`、`README.md`、`tests/integration/test_demo.py`、`CHANGELOG.md`。
- 测试结果：`.venv` 中 `crosserp demo --check --no-browser` 通过，打印 120 组/114 匹配/95%；wheel 构建成功并含包内样本；ruff、mypy、pre-commit；SQLite 全量 `204 passed, 2 skipped`，覆盖率 `86.24%`。
- 偏离计划：演示库已存在时提示换路径，不自动删除，保护本地演示数据；发布前仍用 wheel 路径测试，不发布 PyPI。
