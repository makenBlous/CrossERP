# T26 发布 v0.1.0：release.yml + PyPI Trusted Publishing（发布动作由 maken 操作）

> **当前状态：已被 08 v4 第 8 节取代；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W3 | 0.5 天 | T25（且 maken 已写「同意发布」） | `task/T26-release` |

## 目标
打 `v0.1.0` tag 后自动构建并发布到 PyPI 和 GitHub Release；任何人 `uv tool install crosserp` 就能装。

## 背景
- 实施方案 7.4（发布流程：CHANGELOG → 打 `vX.Y.Z` tag → `release.yml` 构建 wheel/sdist、PyPI Trusted Publishing、GHCR 镜像、GitHub Release → maken 在干净机器重装验证）、8 W3 第 8 条（v0.1.0 发 PyPI）。GHCR 镜像属于 v0.5（Docker 部署），本任务不做。
- PyPI Trusted Publishing（OIDC，不在仓库存 API token）官方说明：https://docs.pypi.org/trusted-publishers/ ；GitHub 官方发布 action：https://github.com/pypa/gh-action-pypi-publish 。具体配置步骤以写任务时官方文档为准（代理实现前重新打开核对，PR 里附链接）。
- `crosserp` 这个名字在 PyPI 上是否可用：本任务文件**未核实**；**发布前 maken 必须自己再查一次**。

## 范围
- `.github/workflows/release.yml`：触发 `push: tags: ["v*.*.*"]`；job `build`（`uv build`，上传 artifact，校验 tag 版本 = `pyproject` 版本，不一致直接失败）；job `publish-testpypi`（environment `testpypi`）→ job `publish-pypi`（environment `pypi`，需要 maken 在 GitHub 设置「Required reviewers」手动批准）；job `github-release`（附 wheel/sdist + CHANGELOG 本版本小节）。权限最小化：只有 publish job 有 `id-token: write`。
- `docs/release.md`：maken 操作手册（PyPI/TestPyPI 上添加 trusted publisher 的步骤、GitHub environment 设置、打 tag 命令、发布后验证命令）。
- `pyproject.toml` 版本 `0.1.0`、classifiers、`project.urls`、`readme`、`license = "Apache-2.0"`。
- 代理**只写文件和文档**。

## 不做（红线）
- 代理**不得**打 tag、push tag、在 PyPI/TestPyPI 注册或配置任何东西、创建 GitHub Release——这些都是对外发布动作，只有 maken 能做。
- 不在仓库或 workflow 里放任何 token/密码。

## 步骤
1. 写 release.yml，用 `act` 或在 fork 上用假 tag 只跑 `build` job 验证（不跑 publish）；做不到就在 PR 里说明，只用 `actionlint` 检查语法（如可用）。
2. 写 `docs/release.md`。

## 涉及文件
`.github/workflows/release.yml` `docs/release.md` `pyproject.toml` `CHANGELOG.md` `README.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 / 检查 | 期望 |
|---|---|
| `uv build` | 生成 `crosserp-0.1.0-py3-none-any.whl` 和 sdist |
| `uv tool install dist/crosserp-0.1.0-py3-none-any.whl && crosserp demo --check` | 退出码 0 |
| workflow 语法检查 | 无错误 |

## maken 人工验收清单（发布由你操作）
- [ ] 在 PyPI 搜一下 `crosserp`，确认名字还空着。
- [ ] 按 `docs/release.md` 在 TestPyPI、PyPI 添加 trusted publisher，在 GitHub 建 `testpypi`、`pypi` 两个 environment（`pypi` 设你为 required reviewer）。
- [ ] 合并 PR 后在本机：`git tag v0.1.0`、`git push origin v0.1.0`；在 Actions 页批准 `publish-pypi`。
- [ ] 在一台干净的电脑（或新建的 Windows 用户）上：安装 uv → `uv tool install crosserp` → `crosserp demo`，计时，记到 `docs/evidence/v0.1-acceptance.md`。

## 问题

## 完成记录
