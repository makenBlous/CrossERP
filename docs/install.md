# 从本地 wheel 安装

T53 的安装检查从本地构建的 wheel 开始，不访问 PyPI。它会初始化 SQLite 数据库、运行合成数据检查、启动本地网页、请求登录页并用初始化账号完成真实登录；计时结果写入 JSON。v1.0 前不发布 PyPI 包。

## Linux / macOS

在仓库根目录执行：

```bash
uv sync --all-extras
uv build
uv run python scripts/install_check.py --wheel 'dist/*.whl'
```

脚本会把临时 uv 工具目录放在项目的 `.ci/` 下，不修改公有 Python 环境。结果默认写到 `.ci/install-timing.json`。

## Windows PowerShell

```powershell
uv sync --all-extras
uv build
uv run python scripts/install_check.py --wheel 'dist/*.whl'
```

浏览器验收可打开脚本输出的本地地址；脚本本身已经验证 `/login` 和登录跳转。若只需要查看计时：

```powershell
Get-Content .ci\install-timing.json
```

## CI 证据

GitHub Actions 的 `install-smoke` 在 Ubuntu、Windows、macOS 三个 runner 上执行同一脚本，并把每个平台的 JSON 上传为 `install-timing-<平台>` artifact。artifact 是测试证据，不是发布产物。
