# T31 审计导出 / 离线校验 / 保留策略 + W4 验收（指标 4）

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W4 | 1.5 天 | T29, T30 | `task/T31-audit-export` |

## 目标
审计记录能打包给会计/审计师，对方不装 CrossERP 也能离线验证没被改过；以后清理日志不会把哈希链弄断。W4 的验收在本任务收口。

## 背景
- 实施方案 8 W4 第 7、8 条与 W4 验收：`audit verify`；`audit export --from --to --format jsonl|csv` 生成 zip（含 manifest.json：条数、首尾 hash、每个文件 sha256），导出动作本身也写审计；`audit verify-export x.zip` 离线校验；config `audit.retention`，业务审计默认永不自动删除，清理任何日志前先写 `audit_checkpoint`。
- 4 节：`audit_checkpoint`（chain, upto_id, upto_hash, reason）、`audit_export`（requested_by, from_ts, to_ts, format, row_count, first_hash, last_hash, file_sha256）。
- 会计档案的法定保管期限**未核实**（实施方案原话：发布前请 maken 向会计确认）。

## 范围
- 迁移 `000x_audit_checkpoint_export`：建上面两张表（若还没有）。
- `crosserp audit export --from YYYY-MM-DD --to YYYY-MM-DD --format jsonl|csv --out x.zip`（日期按 Asia/Shanghai 解释并在 manifest 里写明换算后的 UTC 范围）：
  - zip 内：`audit_log.jsonl`（或 `.csv`，UTF-8 带 BOM 方便 Excel，推断）、`manifest.json`（`format_version`、`crosserp_version`、`from_utc`、`to_utc`、`row_count`、`first_seq`、`last_seq`、`prev_hash_before_first`、`first_hash`、`last_hash`、`files: {名字: sha256}`、`hash_algorithm` 说明）、`VERIFY.md`（不用 CrossERP 如何用 Python 标准库或 `sha256sum` 手工校验的步骤）。
  - 导出本身写 `audit_export` 行 + 审计 `audit.export`（导出范围之外，写在链尾）。
- `crosserp audit verify-export x.zip`：只用 zip 内容（不连数据库）校验：文件 sha256 = manifest；逐行重算哈希链从 `prev_hash_before_first` 接到 `last_hash`；条数一致。通过退出码 0，否则 1 并指出第一处问题。校验逻辑放在 `audit/offline_verify.py`，**只依赖标准库**（方便以后单独分发）。
- 保留：`config` 的 `audit.retention`（默认 `business: never`）；`crosserp audit checkpoint --reason ...` 写 `audit_checkpoint`（upto = 当前链头）；`audit verify --from-checkpoint <id>` 从检查点开始校验。本任务**不实现任何删除命令**（以后清理登录日志/LLM 原文时，删除前必须先写 checkpoint——在 `docs/audit.md` 写成规则）。
- `docs/audit.md`：审计字段说明、导出/校验/检查点用法、「法定保管期限未核实，请向会计确认」。
- W4 验收汇总：`docs/evidence/w4-acceptance.md`，逐条对照实施方案 W4 验收（守卫测试全过并纳入 CI；手改一行审计 → verify 报错；任意凭证可查「谁、何时、改前/改后、谁批准」——W4 没有凭证，用期间利润报表的审批+导出代替，注明；MySQL/PG 上 app 账号 UPDATE audit_log 被拒；导出包离线校验通过、改一个字节后失败），每条附 CI 链接或命令输出。

## 不做
- 不做自动删除/归档任务；不做签名（GPG 等，以后再议）。

## 步骤
1. 先写测试：导出→校验通过；zip 里改 1 个字节（jsonl 任意位置、manifest 任意字段）→ 校验失败；跨检查点校验；空范围导出（0 条）也能生成合法包并校验通过。
2. 实现导出、离线校验、检查点、文档、验收汇总。

## 涉及文件
`src/crosserp/audit/{export,offline_verify,checkpoint}.py` `src/crosserp/db/schema.py` `src/crosserp/db/migrations/versions/000x_audit_checkpoint_export.py` `src/crosserp/config.py` `src/crosserp/cli.py` `docs/audit.md` `docs/evidence/w4-acceptance.md` `tests/integration/test_audit_export.py` `tests/unit/test_offline_verify.py`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run crosserp audit export --from 2026-10-01 --to 2026-12-31 --format jsonl --out a.zip && uv run crosserp audit verify-export a.zip` | 退出码 0 |
| 改 a.zip 里 jsonl 一个字节后 `verify-export` | 退出码 1，指出文件/行 |
| `uv run pytest -m db -k "audit or guard" -q`（三库） | passed |
| `uv run pytest --cov=crosserp --cov-fail-under=60` | passed |

## maken 人工验收清单（W4 验收）
- [ ] 不审批直接导出 → 被拒绝（T28 清单第 1 条再做一次）。
- [ ] `uv run crosserp audit export --from 2026-11-01 --to 2026-12-31 --format csv --out D:\audit.zip`，用 Excel 打开里面的 csv 看一眼，中文不乱码。
- [ ] `uv run crosserp audit verify-export D:\audit.zip` 通过；用 7-Zip 把 csv 里改一个字放回 zip，再校验 → 失败。
- [ ] 读 `docs/evidence/w4-acceptance.md`，每条都有证据。
- [ ] 问一下会计：账务相关记录要保存几年，写进 `docs/audit.md`。

## 问题

## 完成记录
