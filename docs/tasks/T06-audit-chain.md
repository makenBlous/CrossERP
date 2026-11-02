# T06 审计日志：只追加哈希链 append / verify_chain

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W1 | 1 天 | T05 | `task/T06-audit-chain` |

## 目标
任何人改了或删了审计表里任意一行，`crosserp audit verify` 都能发现。

## 背景
- 实施方案 6.6（哈希链、audit_head 行锁）、8 W1 第 6 条。完整字段补全在 W4，本任务做核心链。

## 范围
- `audit/chain.py`：`canonical_json(obj) -> bytes`（`json.dumps(sort_keys=True, ensure_ascii=False, separators=(",",":"))`，Decimal 转字符串、datetime 转 ISO-8601 UTC）；`compute_hash(prev_hash, record) -> str`（`sha256(prev_hash + canonical_json)` 的 hex）。创世 prev_hash = 64 个 `0`。
- `audit/log.py`：
  - `append(session, actor_type, action, target_type, target_id, before, after, **optional) -> AuditLog`：在调用方的事务里写；先锁 `audit_head` 行（通过 `dialects.lock_for_update()`：MySQL/PG `SELECT ... FOR UPDATE`，SQLite 直接读），计算 hash，插入 `audit_log`，更新 head。
  - `verify_chain(session) -> VerifyResult(ok: bool, checked: int, first_bad_id: str | None, reason: str | None)`：按插入顺序（单调序号列 `seq`，若 T05 没有就在本任务加迁移 `0002`）逐行重算。
- CLI：`crosserp audit verify`，成功退出码 0，失败退出码 1 并打印第一条坏记录。
- 不提供任何 update/delete 审计记录的函数。

## 不做
- 不做导出、保留策略、security_event、数据库授权（W4/W5）。

## 步骤
1. 写 chain.py + 单元测试（固定输入 → 固定 hash，写死在测试里作为回归基准）。
2. 写 log.py；如需 `seq` 列，新增 Alembic 迁移并确保三库往返。
3. 测试 `tests/integration/test_audit_chain.py`（`db` marker）：
   - 追加 5 条 → verify ok，checked=5；
   - 直接用 SQL 改第 3 条的 `after_json` → verify 返回 ok=False 且 first_bad_id=第 3 条；
   - 删除第 2 条 → verify 失败；
   - 事务回滚时审计记录也不存在。
4. hypothesis：随机生成 1–30 条记录，随机篡改其中一条的任意字段，verify 必须失败。

## 涉及文件
`src/crosserp/audit/chain.py` `src/crosserp/audit/log.py` `src/crosserp/db/dialects.py` `src/crosserp/db/migrations/versions/0002_*.py`（如需要） `src/crosserp/cli.py` `tests/unit/test_audit_hash.py` `tests/integration/test_audit_chain.py` `tests/property/test_audit_tamper.py` `CHANGELOG.md`

## 验收标准
| 命令 | 期望 |
|---|---|
| 三库分别 `uv run pytest -m db -k audit -q` | 全部 passed |
| `uv run crosserp audit verify`（空库） | `审计链完整：0 条`，退出码 0 |
| `uv run pytest tests/property -k tamper -q` | passed |

## maken 人工验收清单
- [ ] 运行代理提供的演示命令（在 PR 里写）往审计表写几条记录，再运行 `uv run crosserp audit verify`，看到「完整」。
- [ ] 用 DBeaver 手动改其中一条记录的任意文字，再运行 `uv run crosserp audit verify`，看到报错并指出是哪一条。

## 问题

当前本地验收只跑 SQLite。MySQL 8.4 和 PostgreSQL 18 的 `pytest -m db -k audit` 没有实跑。本机没有可用的 MySQL / PostgreSQL。没有编造三库输出。代码仍按三库兼容写。`lock_for_update()` 在 MySQL / PostgreSQL 上加 `FOR UPDATE`。SQLite 直接读。

以下是推断。没有停下来问。若不同意请改：

- 业务链名是 `audit_log`。以后的 `security_event` 另开一条链。
- 创世 `prev_hash` 是 64 个 `0`。`hash = sha256(prev_hash 的 UTF-8 字节 + canonical_json 字节)` 的 hex。`Decimal` 用 `format(d, "f")`。时间用带微秒的 ISO-8601 UTC，后缀 `+00:00`。
- 哈希覆盖除 `hash` 以外的全部列。先写入再读回后计算。避免时间精度在三库上不一致。
- `seq` 由应用从 1 递增分配。类型是 `Integer`。唯一约束 `uq_audit_log_seq`。不用数据库自增。
- `crosserp audit verify` 会先把库迁移到 head。空库和只跑过 `0001` 的库可以直接校验。
- 不在追加时开 SAVEPOINT。当前 SQLite 驱动可能把 SAVEPOINT 提前提交。两条连接同时第一次建链头时，唯一约束失败，整个事务回滚。
- 另外改了 `schema.py`、`core/models.py` 的 `AuditLogRecord.seq`，以及 `docs/architecture.md` 的表清单。任务文件没有列出这三处。不加的话表、模型和文档会对不上。

## 完成记录

当前分支 `task/T06-audit-chain`。未推送。未把状态改成 done。未改 `docs/tasks/README.md`。

2026-11-02 在本 worktree 实际运行。解释器 `D:\make\write\work\CrossERP\.venv\Scripts\python.exe`。未使用 `uv run`。未创建或删除虚拟环境。`PYTHONPATH` 指向本 worktree 的 `src`。未设置 `CROSSERP_TEST_DATABASE_URL`。数据库是 SQLite。

| 命令 | 结果 |
|---|---|
| `python -m pytest -q` | 退出码 0。`106 passed, 1 skipped, 1 warning in 5.73s`。跳过的是没有 MySQL 的自检测试 |
| `python -m pytest -m db -k audit -q` | 退出码 0。`9 passed, 98 deselected, 1 warning in 3.15s` |
| `python -m pytest tests/property -k tamper -q` | 退出码 0。`1 passed, 7 deselected in 1.02s` |
| `python -m pytest --cov=crosserp --cov-fail-under=60 -q` | 退出码 0。覆盖率 88.46%。`106 passed, 1 skipped, 1 warning in 6.31s` |
| `python -m crosserp.cli --version` | 退出码 0。`0.0.1` |
| `python -m crosserp.cli audit verify`（临时空 SQLite） | 退出码 0。`审计链完整：0 条` |
| 写入 3 条后再运行 `python -m crosserp.cli audit verify` | 退出码 0。`审计链完整：3 条` |
| 用 SQL 改第 2 条 `after_json` 后再运行 `python -m crosserp.cli audit verify` | 退出码 1。stderr：`审计链损坏：第一条坏记录 ac069a65-b5dc-46b2-9624-7af6b774e4ed。哈希与记录内容不一致`。该 id 是第 2 条 |
| `python -m alembic -c src/crosserp/db/alembic.ini check`（已迁移的临时 SQLite） | 退出码 0。`No new upgrade operations detected.` |
| `ruff check`（本任务改过的文件） | 退出码 0。All checks passed |
| `mypy` | 退出码 0。Success: no issues found in 32 source files |

maken 可复制的演示。先在临时库看完整，再用 SQL 改一条后看报错。把 `CROSSERP_DATABASE_URL` 换成自己的空库即可。本环境没有 `uv run`。等价命令是 `python -m crosserp.cli`。

```powershell
$env:PYTHONPATH = "<worktree>\src"
$env:CROSSERP_DATABASE_URL = "sqlite:///C:/temp/crosserp-audit-demo.db"
python -m crosserp.cli audit verify
```

空库输出：

```text
审计链完整：0 条
```

写入后再校验，输出 `审计链完整：N 条`，退出码 0。用 DBeaver 或 SQL 改任意一条的文字后再运行同一条命令，退出码 1，并打印第一条坏记录的 id。
