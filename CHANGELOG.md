# Changelog

本文件格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### 新增

- 对账异常分类草案 `docs/rules/recon-categories.md`，以及原因码人话模板草稿。5 个原因码已由 maken 于 2026-11-02 确认。
- v0.1 业务表、初始迁移和 `crosserp init`。已确认的 5 个原因码写入 `IssueKind`。
- GitHub Actions：三系统测试，以及 SQLite / MySQL 8.4 / PostgreSQL 18 检查。
- 导入协议、连接器注册表和按 sha256 去重的导入批次。坏行记 `PARSE_ERROR` 后继续。
- 只追加审计哈希链，以及 `crosserp audit verify`。
- 金额类型 `Money` 与 `parse_amount()`。全程 `Decimal`，禁止 float。
- 数据库类型 `Money4`、`FxRate`、`UtcDateTime`，以及 `crosserp db check`。当前默认 SQLite，切换库只改配置文件。
- 固定种子合成样本生成器，以及 `samples/synthetic/` 标准答案。
- `crosserp serve` 启动本机网页（默认只监听 127.0.0.1:8000）。首页显示「CrossERP 运行中」和版本号，`/health` 返回 `{"status":"ok","version":"0.0.1"}`。
- 运行依赖增加 `uvicorn`（只写下限），用于启动 FastAPI。页面引用官方 npm 包 htmx.org 2.0.11 的 `htmx.min.js`，未做交互。
- 初始化可安装的 `crosserp` 空包，并提供 `crosserp --version`。
