# Changelog

本文件格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### 新增

- 对账异常分类草案 `docs/rules/recon-categories.md`，以及原因码人话模板草稿。5 个原因码已由 maken 于 2026-11-02 确认。
- v0.1 业务表、初始迁移和 `crosserp init`。已确认的 5 个原因码写入 `IssueKind`。
- GitHub Actions：三系统测试，以及 SQLite / MySQL 8.4 / PostgreSQL 18 检查。
- 导入协议、连接器注册表和按 sha256 去重的导入批次。坏行记 `PARSE_ERROR` 后继续。
- 只追加审计哈希链，以及 `crosserp audit verify`。
- 通用映射导入器，可读 YAML 列映射的订单、成本、汇率和 SKU。领星、赛狐表头仍待真实数据验证。
- Shopify Payments 打款 CSV 导入器。
- Amazon Settlement Flat File V2 导入器。
- `crosserp import`、`crosserp demo-import` 和 `crosserp issues list`。
- 失败批次可以重导。文件打不开也记一条失败批次，`sha256` 留空。
- 金额类型 `Money` 与 `parse_amount()`。全程 `Decimal`，禁止 float。
- 数据库类型 `Money4`、`FxRate`、`UtcDateTime`，以及 `crosserp db check`。当前默认 SQLite，切换库只改配置文件。
- 固定种子合成样本生成器，以及 `samples/synthetic/` 标准答案。
- `crosserp serve` 启动本机网页（默认只监听 127.0.0.1:8000）。首页显示「CrossERP 运行中」和版本号，`/health` 返回 `{"status":"ok","version":"0.0.1"}`。
- 运行依赖增加 `uvicorn`（只写下限），用于启动 FastAPI。页面引用官方 npm 包 htmx.org 2.0.11 的 `htmx.min.js`，未做交互。
- 初始化可安装的 `crosserp` 空包，并提供 `crosserp --version`。
- 三库实测文档、Docker 启动脚本和跨 SQLite/MySQL 8.4/PostgreSQL 18 的金额、时间、字符与迁移往返测试；修复 MySQL 初始迁移回滚时外键索引删除顺序。
- 导入批次规则：只有成功批次按 sha256 拒绝重复，失败批次可重导并保留重试关系；打不开的文件留失败记录，running 批次可手动标记失败。
- 原因码正式目录 `issues/catalog.yaml`、中文说明渲染和统一异常写入服务；`crosserp issues list` 显示原因名称与人话模板。
- 确定性的对账引擎核心：按平台订单号/SKU 分组匹配、规则注册表、可追溯的 `recon_run`，以及未匹配原因码和重跑保留旧结果。
- 对账补充规则：待下期、配送费多收费、拒付、部分退款和重复结算；新增配送费参考导入和 `reconcile` 摘要统计。
- 确定性利润计算：订单/SKU 原币与人民币利润、成本生效期、月汇率、缺成本/缺汇率异常、输入哈希和可复用利润快照。
- Golden 逐分比对命令 `crosserp check-golden`、合成利润/异常标准答案和差异报告。
- Excel/CSV 利润报表、异常清单和说明页；`reconcile --json` 机器可读输出。
