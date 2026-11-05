# T39 凭证草稿：会计科目映射 `accounts.yaml` + `voucher` / `voucher_line` 表 + 借贷平衡（⚠ 待 maken 确认）

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| review | W6 | 2 天 | T38 | `main` |

## 目标
从已对账、已算利润的结算数据，自动生成「凭证草稿」：每张凭证若干分录，借方合计必须等于贷方合计（分毫不差，用 Decimal）；科目由 maken 可改的 `accounts.yaml` 决定；草稿可提交审批，审批对象类型为 `voucher`。

## 背景
- 实施方案 8 W6 第 1、2 条；2.3 节凭证；0 节红线「AI 不算钱」（本任务无 AI，全部确定性代码）。
- W4 证据记录：凭证当时**未实现**，W4 改用「利润报表审批 + 导出」走通流程。本任务补上凭证。
- 仓库现状：`core/` 有 Decimal 金额工具；`profit/` 有利润计算；`approval.target_type String(32)`、`target_id String(128)` 足够放 `voucher` 和凭证 UUID；`ledger/write_service._payload_hash` 目前只认利润报表（T40 重构）。
- 下一个迁移号：T32 用 0012、T34 用 0013，本任务 **0014**。
- 会计科目编码：**未核实**——各家企业科目表不同，财政部《企业会计准则》一级科目编码只作参考；代理不得编造「某科目编码一定是 xxxx」，只给模板占位。

## 范围
- `src/crosserp/vouchers/`：`model.py`（`VoucherDraft`、`VoucherLineDraft` 数据类，金额用 `crosserp.core.money.Money`/`Decimal`；分录金额在生成凭证时按 `ROUND_HALF_UP` 定到 2 位（凭证是最终展示/输出口径，符合 AGENTS「只在最终展示时舍入」），尾差进入单独一行「舍入差」分录或并入最大一行（⚠ Q4））、`accounts.py`（读取并校验 `accounts.yaml`）、`builder.py`（结算/利润 → 凭证）、`service.py`（保存、列出、提交审批）。
- `accounts.yaml` 默认位置与示例（⚠ Q1）：每项 `key`（如 `sales_revenue`、`platform_fee`、`ad_cost`、`fx_diff`、`platform_receivable`）→ `code`、`name`、`direction`；示例文件里 code 写成 `"待填-1122"` 这类占位并在注释里写「请按贵司科目表填写」。缺 key 或 code 以「待填」开头时，生成凭证报中文错误并列出缺哪些。
- 迁移 `0014_voucher`：
  - `voucher`：`id Uuid PK`、`store_id`、`period String(7)`、`source_type String(32)`（`settlement`/`month`）、`source_id String(128)`、`state String(16)`（draft/submitted/approved/rejected/exported/void）、`currency String(3)`、`total_debit Money4`、`total_credit Money4`（AGENTS §4：金额列一律 `Money4`）、`inputs_hash String(64)`、`accounts_hash String(64)`（accounts.yaml 内容哈希，科目改了旧审批失效）、`created_by String(64)`、`created_at`；唯一约束 `(store_id, period, source_type, source_id)` 中「非 void」的那张（用应用层保证 + 测试，不依赖部分索引，三库一致）。
  - `voucher_line`：`id`、`voucher_id FK`、`line_no`、`account_key String(64)`、`account_code String(32)`、`account_name String(128)`、`debit Money4`、`credit Money4`、`summary String(200)`、`source_ref String(128)`（指向 settlement_line / profit_snapshot，便于追溯）。
- 数据库层 CHECK：`debit >= 0 AND credit >= 0 AND NOT (debit > 0 AND credit > 0)`；整张凭证平衡在 service 层校验，保存时若 `total_debit != total_credit` 直接拒绝（不允许存不平的草稿）。
- 生成粒度（⚠ Q2）：先实现一种，另一种留接口。
- 外币：结算币种 → 记账本位币用现有 `fx` 汇率表；汇率差进 `fx_diff` 科目；找不到汇率 → 不生成，开一条 issue（复用 `issues.service.open_issue`，kind 需在 `catalog.yaml` **追加** `voucher_fx_missing`）。
- 审批：`approval` 新对象类型 `voucher`，`target_id = voucher.id`；`payload_hash = sha256(inputs_hash + accounts_hash + 规范化分录)`；在 `approval/` 增加按 `target_type` 分发的 payload 计算函数（`profit_report` 原逻辑原样搬过去，行为不变）。
- CLI：`crosserp voucher draft --store ... --period YYYY-MM [--by settlement|month] --as ...`、`voucher list`、`voucher show <id>`（中文表格，借贷合计）、`voucher submit <id> --as ...`。
- 审计：生成、作废、提交都写 `audit_log`（`target_type="voucher"`）。
- 授权脚本：新表给 app 账号 SELECT/INSERT/UPDATE（不 DELETE）；agent 只读账号给 SELECT（T42 要查）。
- 提交：`main`，`feat(vouchers): add voucher drafts with balanced lines (T39)`；测试不过不提交；不发布。

## 不做
- 不写出到任何外部格式（T40、T41）；不做手工新增分录的网页编辑（⚠ 后续再议）；不做多本位币。

## 步骤
1. 先写测试：
   - 性质测试（hypothesis）：任意合法结算数据生成的凭证，`sum(debit) == sum(credit)`，且每行最多一边非零。
   - 黄金样例：用 demo 数据 8 个可运行 SKU 生成凭证，期望分录写成 `tests/golden/voucher_demo.yaml`（**期望值由代理按规则手算一次并在完成记录列出计算过程，maken 抽查**）。
   - accounts.yaml 缺项 → 中文报错；改 accounts.yaml → 已提交凭证审批 `check_fresh` 失败。
   - 同一来源重复生成 → 拒绝（除非先作废）。
   - 原有 `profit_report` 审批测试原样通过。
2. 迁移（三库升级/降级测试）→ 模型 → builder → service → CLI。
3. 更新 `scripts/sql/grant_*.sql` 并跑 grants 测试。

## 涉及文件
`src/crosserp/vouchers/{__init__,model,accounts,builder,service}.py` `config/accounts.example.yaml`（⚠ Q1） `src/crosserp/db/schema.py` `src/crosserp/db/migrations/versions/0014_voucher.py` `src/crosserp/db/repo/vouchers.py` `src/crosserp/approval/{payload,service}.py` `src/crosserp/issues/catalog.yaml`（只追加） `src/crosserp/cli.py` `scripts/sql/grant_*.sql` `tests/unit/vouchers/` `tests/property/test_voucher_balance.py` `tests/golden/voucher_demo.yaml` `tests/integration/test_voucher_db.py` `docs/vouchers.md` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/vouchers tests/property -q` | passed |
| `uv run pytest -m db -k "voucher or approval or grants or migration" -q`（三库） | passed |
| `uv run crosserp demo && uv run crosserp voucher draft --store <demo 店铺> --period <demo 月份> --as maken` | 生成成功，`voucher show` 借贷合计相等 |
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] 打开 `config/accounts.example.yaml`，把科目编码换成你们公司（或你熟悉的）科目表的编码，另存为说明里写的位置。
- [ ] `uv run crosserp demo`，然后按 `docs/vouchers.md` 的命令生成一张凭证，`voucher show` 看：借方合计 = 贷方合计。
- [ ] 抽一条分录，对照 demo 的结算表手算一下金额是否对得上（完成记录里有代理的计算过程）。
- [ ] 把 accounts.yaml 里删掉一项再生成：提示缺哪一项。

## 问题
- **Q3 已由 maken 决定：按 A 执行，并补充收入、平台费用、广告费、退款、打款、汇兑差的借贷方向。** 所有科目编码和方向都在 `accounts.yaml`，默认值标注「待会计核实」；不平衡不生成。当前 T39 先实现按月利润快照草稿，结算单粒度和打款到账分录留接口，后续任务接入。
- Q1、Q2、Q4 按任务文件推荐默认执行：科目文件使用 `~/.crosserp/accounts.yaml` 并支持 `CROSSERP_ACCOUNTS_FILE`；当前先按店铺月份生成；两位小数尾差并入金额最大行并在摘要说明。科目编码仍标「待会计核实」，不会冒充真实科目表。

- **Q4 ⚠ 待 maken 确认：凭证 2 位小数舍入后的尾差怎么处理。** 选项：A 并入金额最大的一行并在摘要注明（推荐，常见做法，推断）；B 单列「舍入差」科目（需在 accounts.yaml 加一项）。

## 完成记录
- maken 决定：Q3 选择 A，并明确销售、平台费用、广告费、退款、打款、汇兑差方向；按决定实现，科目编码与方向均由 `accounts.yaml` 提供。
- 完成内容：新增 `vouchers` 领域模型、YAML 科目映射校验与内容哈希、按店铺月份利润快照确定性生成凭证、Decimal 最终两位舍入、借贷平衡和单行单边校验、来源去重；新增 `voucher`/`voucher_line` 表及 0014 迁移；新增凭证审批 payload 哈希；新增 `voucher draft/list/show/submit` CLI；补充文档和示例科目配置。
- 修改文件：`src/crosserp/vouchers/`、`src/crosserp/approval/payload.py`、`src/crosserp/db/schema.py`、`src/crosserp/db/migrations/versions/0014_voucher.py`、`src/crosserp/db/repo/vouchers.py`、`src/crosserp/cli.py`、`config/accounts.example.yaml`、`docs/vouchers.md`、`tests/unit/vouchers/`、`tests/integration/test_voucher_db.py`、`CHANGELOG.md`。
- 测试结果：`.venv/bin/ruff check .`、`.venv/bin/mypy`、`.venv/bin/pre-commit run --all-files` 通过；凭证单元/数据库/审批测试 10 passed；全量 SQLite `.venv/bin/pytest -q --cov=crosserp --cov-fail-under=60` 为 244 passed、7 skipped，覆盖率 80.51%；MySQL 8.4 迁移/凭证抽查 6 passed、1 skipped，PostgreSQL 18 迁移/凭证抽查 6 passed、1 skipped；CLI demo + voucher draft 实测借贷均为 485.58。
- 手算抽查：示例收入 10.00、平台费 1.25、退款 2.00；借方平台应收 10.00 + 平台费用 1.25 + 收入冲减 2.00 = 13.25，贷方销售收入 10.00 + 平台应收 1.25 + 平台应收 2.00 = 13.25，逐分相等。
- 偏离计划：按 maken 决定先实现按月粒度；按结算单生成、平台打款到账和汇兑差的具体数据接入保留接口，待后续已有结算/汇率数据路径接入；没有修改已合并表结构或新增依赖。
