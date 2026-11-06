# W10 安装计时证据

## CI

T53 已把 `install-smoke` 改为本地 wheel 安装检查：构建 wheel、初始化管理员、运行 demo、启动服务、请求 `/login` 并完成真实登录；Ubuntu、Windows、macOS 的 JSON 由 Actions artifact `install-timing-<平台>` 保存。

当前分支的远程 Actions 计时结果：未核实（本地未执行 GitHub Actions）。

## Linux 本机

运行命令：

```bash
uv build
uv run python scripts/install_check.py --wheel 'dist/*.whl'
```

本机一次实测结果（2026-11-06，Linux，Python 3.14.10）：uv 检查 0.004 秒，wheel 安装 0.113 秒，初始化 3.758 秒，demo 3.752 秒，启动并检查服务 0.819 秒，登录 0.119 秒，总计 8.780 秒；`login_success=true`。完整 JSON 写入 `.ci/install-timing.json`，该目录已被忽略，不提交临时路径和数据库。

Windows 实测由 maken 按 `docs/install.md` 补充；macOS/Windows CI artifact 结果待远程 Actions 运行后补充。
