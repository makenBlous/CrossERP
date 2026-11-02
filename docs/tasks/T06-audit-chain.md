# T06 审计日志：只追加哈希链 append / verify_chain

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W1 | 1 天 | T05 | `task/T06-audit-chain` |

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

## 完成记录
