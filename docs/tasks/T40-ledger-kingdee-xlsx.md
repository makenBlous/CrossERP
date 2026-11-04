# T40 写出目标重构 + 金蝶导入模板 `kingdee_xlsx`（表头可配置，⚠ 待真实模板验证）

| 状态 | 周 | 估时 | 依赖 | 提交位置 |
|---|---|---|---|---|
| todo | W6 | 1.5 天 | T39 | `main` |

## 目标
已批准的凭证能导出成金蝶可导入的 Excel；表头和列顺序写在配置里，拿到真实模板后改配置即可，不改代码。导出仍然只能经过 `ledger/write_service.py` 这一个入口、仍然要一次性审批 token。

## 背景
- 实施方案 8 W6 第 3 条；0 节红线「写账必须审批」。
- 仓库现状（红线代码，改动要格外小心）：
  - `ledger/write_service.export(session, batch_id, target_id, approval_token, *, output_dir)`：独立会话校验审批 → 生成 → 记录 `ExportArtifact` → 消费 token；拒绝时 `_record_denial` 写审计。
  - `_payload_hash` 只支持 `店铺:YYYY-MM` 利润报表；`_target` 只支持 `"xlsx"`。
  - `ledger/targets/base.py::LedgerTarget` 协议：`id` + `render(session, *, batch_id, approval_id, output_dir) -> Path`。
  - AST 守卫测试：除 `write_service` 外任何模块不得 import `ledger.targets`。
  - `export_artifact.target_id String(32)`（`kingdee_xlsx` 12 个字符，够用）。
- 金蝶产品线（KIS / 精斗云 / 云星空等）凭证导入模板格式不同，**未核实**，见 Q1。

## 范围
- 重构（行为不变）：
  - `_payload_hash` 改为调用 T39 的 `approval.payload.compute(target_type, target_id)`，`profit_report` 分支逻辑原样。
  - `_target(target_id)` 改为注册表 `TARGETS = {"xlsx": ..., "kingdee_xlsx": ..., "generic_xlsx": ...}`（generic 在 T41 实现，本任务先占位抛 `UNKNOWN_TARGET`）；每个目标声明支持的审批对象类型（`xlsx` 只支持 `profit_report`，`kingdee_xlsx` 只支持 `voucher`），不匹配 → `ApprovalRequired("TARGET_TYPE_MISMATCH", ...)` 并写拒绝审计。
- `ledger/targets/kingdee_xlsx.py`：读取 `ledger/templates/kingdee_voucher.yaml`（列名、列顺序、日期格式、凭证字、金额格式、科目列用编码还是「编码 名称」），用 openpyxl 写；文件名 `voucher_<店铺>_<期间>_<审批ID前8位>.xlsx`；**不覆盖**已存在文件（沿用 xlsx 目标做法）。
- 模板配置首版按「常见列」起草：凭证日期、凭证字、凭证号、摘要、科目编码、科目名称、借方金额、贷方金额、币别、汇率、原币金额，并在 yaml 顶部注释「待真实模板验证」。
- 守卫测试保持并补充：新目标文件也只能被 write_service import；`export` 外不得调用 `render`。
- 提交：`main`，`refactor(ledger): dispatch payload and targets by type (T40)` 与 `feat(ledger): add kingdee xlsx target (T40)` 两个提交（先重构、全部旧测试通过后再加功能）；测试不过不提交；不发布。

## 不做
- 不调用金蝶任何 API（只出文件，人工导入）；不做用友（⚠ 后续）。

## 步骤
1. 先跑一遍全部 `tests/**/ledger*` `tests/**/export*` 记下用例数；重构后用例数不减且全过。
2. 写测试：kingdee 导出文件表头与 yaml 一致；金额单元格是数值且 2 位小数；借贷合计行与凭证一致；未批准 / token 已用 / 凭证改过 / 目标类型不匹配 → 拒绝且有审计；同一 token 不能导两次。
3. 实现模板读取与写出。

## 涉及文件
`src/crosserp/ledger/write_service.py` `src/crosserp/ledger/targets/{__init__,kingdee_xlsx}.py` `src/crosserp/ledger/templates/kingdee_voucher.yaml` `src/crosserp/approval/payload.py` `src/crosserp/cli.py`（`export --target kingdee_xlsx`） `tests/unit/ledger/` `tests/guard/test_ledger_imports.py`（只追加） `tests/integration/test_voucher_export.py` `docs/vouchers.md` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 | 期望 |
|---|---|
| `uv run pytest tests -k "ledger or export or guard" -q` | passed，用例数 ≥ 重构前 |
| `uv run pytest -m db -k "export or voucher" -q`（三库） | passed |
| 按 `docs/vouchers.md` 跑一遍「生成→提交→批准→导出」 | 得到 xlsx；再用同一 token 导出被拒 |
| 全量检查 | 全过 |

## maken 人工验收清单
- [ ] 按 `docs/vouchers.md` 的步骤生成、提交、批准（用 fin1）、导出一张凭证。
- [ ] 用 Excel 打开导出的文件，看列名和金额。
- [ ] 如果你手上有金蝶的「凭证引入模板」，把它放到 `docs/templates/`（**去掉真实数据**）并告诉代理，代理按它改 `kingdee_voucher.yaml`。
- [ ] 把同一个审批再导出一次：被拒绝。

## 问题
- **Q1 ⚠ 待 maken 确认：用哪个金蝶产品线。** 选项：A 金蝶云星空（中大型常用）；B 金蝶精斗云 / KIS（小微常用）；C 暂不定，先出「常见列」版本，拿到真实模板再改配置（推荐）。模板格式**待真实模板验证**。

## 完成记录
（代理填写）
