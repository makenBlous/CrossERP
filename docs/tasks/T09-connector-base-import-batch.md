# T09 连接器协议 + 注册表 + 导入批次（sha256 去重、坏行不中断）

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W2 | 1.5 天 | T05 | `task/T09-connector-base` |

## 目标
定义所有导入器共用的接口和「导入一批文件」的通用流程，后面的 Amazon/Shopify/映射导入器只需实现解析部分。

## 背景
- 实施方案 2.3（`FileConnector` / `ApiConnector` / `LedgerTarget` 协议，entry point 注册，provenance）、8 W2 开头和第 4 条。

## 范围
- `connectors/base.py`：按实施方案 2.3 定义 `SourceKind`、`FileConnector`、`ApiConnector` 协议（`LedgerTarget` 只放类型定义和注释「v0.5 由 ledger.write_service 使用」，不实现）。
- `core/models.py` 补充：`RawRow{row_no, payload: dict[str,str], source_file}`、`Provenance{connector_id, connector_version, import_batch_id, source_file, row_no}`、`ColumnMapping`、`CanonicalRecord`（判别联合：`SettlementHeader | SettlementLineRec | OrderLineRec | SkuCostRec | FxRateRec | IssueRec`）。
- `connectors/registry.py`：通过 `importlib.metadata.entry_points(group="crosserp.connectors")` 发现连接器；内置连接器也走 entry point（在 pyproject 注册）；`detect(path) -> FileConnector`：各连接器 `sniff()` 取最高分，最高分 < 0.5 或并列 → 抛 `UnknownFileTypeError`（中文提示用 `--type` 指定）。
- `connectors/importer.py`：`import_file(session, path, connector, mapping=None) -> ImportResult`：
  1. 计算文件 sha256；已存在 `import_batch` → 抛 `DuplicateImportError`（中文提示含首次导入时间）。
  2. 建 `import_batch(status=running)`；逐行 `read()` → 写 `raw_row`（原样 payload）→ `normalize()` → 写标准表，每条带 provenance。
  3. 单行解析失败：写一条 `issue(kind=PARSE_ERROR, detail_json={row_no, error, raw})`，继续下一行；`error_count += 1`。
  4. 结束：`status = done`（有错也是 done，错误数另计）；整批异常（如文件读不了）→ 回滚并 `status=failed`。
  5. 写一条审计 `audit.append(action="import", ...)`（同一事务）。
- 一个测试用的假连接器 `tests/fixtures/fake_connector.py`（读简单 CSV），用来测通用流程。

## 不做
- 不实现任何真实平台解析（T10–T12）；不做 CLI（T13）；不做 ApiConnector 实现。

## 步骤
1. 写 models、base、registry、importer。
2. 测试 `tests/integration/test_importer.py`（`db` marker，三库）：
   - 假连接器导入 10 行 → `raw_row` 10 行、`import_batch.row_count=10`；
   - 同一文件再导入 → `DuplicateImportError`，数据库行数不变；
   - 第 4 行故意坏 → 9 行成功 + 1 条 `PARSE_ERROR`，`error_count=1`；
   - 每条标准记录都能通过 `raw_row_id` 找回原始行号；
   - 审计链 verify 仍 ok。
3. `tests/unit/test_registry.py`：sniff 并列和低分的报错。

## 涉及文件
`src/crosserp/connectors/base.py` `src/crosserp/connectors/registry.py` `src/crosserp/connectors/importer.py` `src/crosserp/core/models.py` `src/crosserp/core/errors.py` `src/crosserp/db/repo/imports.py` `pyproject.toml`（entry-points） `tests/fixtures/fake_connector.py` `tests/integration/test_importer.py` `tests/unit/test_registry.py` `docs/architecture.md`（连接器一节） `CHANGELOG.md`

## 验收标准
| 命令 | 期望 |
|---|---|
| 三库分别 `uv run pytest -m db -k importer -q` | passed |
| `uv run pytest tests/unit/test_registry.py -q` | passed |
| `uv run mypy` | 无错误 |

## maken 人工验收清单
- [ ] 读 PR 描述里的「导入流程」说明（应该是人话），确认：重复文件会被拒、坏行不会让整批失败、每条数据能追溯到原文件第几行。
- [ ] 运行 `uv run pytest -q`，全部通过。

## 问题

- maken 于 2026-11-03 决定：只有成功批次才算重复。失败批次可以重导，旧失败记录保留。文件打不开也写一条失败批次，`file_sha256` 留空。已按此实现。
- T06 尚未完成。本任务按 T06 已写明的签名实现了最小 `append` / `verify_chain`，没有加 `crosserp audit verify`。T06 若改哈希规范化，需要和这次写入对齐。

## 完成记录

本地只用 SQLite。解释器是 `D:\make\write\work\CrossERP\.venv\Scripts\python.exe`。`PYTHONPATH` 指向本 worktree 的 `src`。没有用 `uv run`。没有跑 MySQL / PostgreSQL。

```text
pytest -m db -k importer -q
4 passed, 99 deselected, 1 warning in 1.91s

pytest tests/unit/test_registry.py -q
8 passed in 0.24s

mypy
Success: no issues found in 35 source files

pytest -q
102 passed, 1 skipped, 1 warning in 4.19s
```

未改 `docs/tasks/README.md`。未加 `crosserp import`（那是 T13）。`init` / `serve` / `db` 仍在。
