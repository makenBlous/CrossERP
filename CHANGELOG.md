# Changelog

本文件格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### 新增

- 金额类型 `Money` 与 `parse_amount()`。全程 `Decimal`，禁止 float。
- `crosserp serve` 启动本机网页（默认只监听 127.0.0.1:8000）。首页显示「CrossERP 运行中」和版本号，`/health` 返回 `{"status":"ok","version":"0.0.1"}`。
- 运行依赖增加 `uvicorn`（只写下限），用于启动 FastAPI。页面引用官方 npm 包 htmx.org 2.0.11 的 `htmx.min.js`，未做交互。
- 初始化可安装的 `crosserp` 空包，并提供 `crosserp --version`。
