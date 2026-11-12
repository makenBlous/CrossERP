# T53 安装矩阵计时：三系统从零到看到首页（不经 PyPI）（⚠ 待 maken 确认）

> **当前状态：部分；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W10 | 1 天 | T52 | `main` |

## 目标
记录 Windows / macOS / Linux 上「从零安装到打开首页并登录」各花多少分钟，作为 v0.5 指标「安装 ≤ 15 分钟」的证据；因为不发布到 PyPI，安装来源改为本地 wheel。

## 背景
- 实施方案 v0.5 指标（安装时间）与 8 W10 第 1 条。
- 现有 CI `install-smoke`（3 系统，构建 wheel → 安装 → `demo --check`）；本任务扩展为计时并加登录检查。
- 决定「v1.0 前不发布」：不能 `pip install crosserp`，见 Q1。

## 范围
- `scripts/install_check.py`（跨平台，标准库）：记录每步耗时：安装 uv（如未装）→ `uv tool install dist/crosserp-*.whl` → `crosserp init` → `crosserp demo` → 启动 `serve` → 请求 `/login` 200 → 用 init 生成的账号登录成功 → 总耗时写 JSON。
- CI `install-smoke` 改用该脚本，上传计时 JSON 为 artifact（artifact 不是发布）。
- `docs/install.md`：三系统步骤；Windows 用 PowerShell 命令。
- `docs/evidence/W10-install.md`：CI 三系统计时 + maken 本人 Windows 实测（待补）。
- 提交：`main`，`ci: time install matrix from local wheel (T53)`；测试不过不提交；不发布。

## 不做
- 不发 PyPI；不做安装器（exe/msi）。

## 步骤
1. 本机（Linux）跑 `install_check.py` 并记录；macOS/Windows 结果来自 CI（需 Q1 of T51 的结论决定是否能 push）或 maken 实测。

## 涉及文件
`scripts/install_check.py` `.github/workflows/ci.yml` `docs/install.md` `docs/evidence/W10-install.md` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv build && python scripts/install_check.py --wheel dist/*.whl` | 每步耗时 JSON，登录成功 |
| CI install-smoke 三系统 | 绿色（取决于 T51 Q1；不能 push 时标「未核实」） |

## maken 人工验收清单
- [ ] 在一台没装过的 Windows 电脑（或新建用户）上，按 `docs/install.md` 从头装一遍，用手机计时，到看到首页并登录成功为止，把分钟数写进 `docs/evidence/W10-install.md`。

## 问题
- Q1 按推荐默认：由 maken 把本地 wheel 文件直接发给内部试用者；本任务不发布 PyPI。

## 完成记录
- 完成内容：新增跨平台 `scripts/install_check.py`，用本地 wheel 安装到项目 `.ci/uv-tools`，执行 init、demo、serve、`/login` 和真实账号登录；CI 三系统上传 JSON artifact；新增安装文档和 W10 证据模板。
- 按推荐默认：不上 PyPI，内部试用者由 maken 直接分发 wheel。
- Linux 本机实测：Python 3.14.10，uv 检查 0.004 秒，wheel 安装 0.113 秒，初始化 3.758 秒，demo 3.752 秒，服务 0.819 秒，登录 0.119 秒，总计 8.780 秒，登录成功。
- 静态检查：ruff、mypy、pre-commit 通过；远程 Actions 的 Windows/macOS 计时待运行后补充，Windows 人工实测待 maken 补充。
