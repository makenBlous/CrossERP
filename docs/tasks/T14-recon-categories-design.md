# T14 对账异常分类设计（为 W3 做准备，只写文档和枚举草案）

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| todo | W2 | 0.5 天 | T08 | `task/T14-recon-categories` |

## 目标
在 W3 写对账代码之前，把「对不上的单子分哪几类、每类怎么判断、给用户什么人话说明、建议什么处理」定成一份文档，让 maken 确认。

## 背景
- 实施方案 6.1（原因码列表）、6.2（对账伪代码）、6.5（AI 只做解释和建议）。
- 参考两个公开的「LedgerPilot AI」黑客松/演示仓库，**只借鉴思路，不复制任何代码或文字**：
  - https://github.com/Varun-AI-Robotics/ledgerpilot-ai ——README 把对账结果分为 `MATCHED / FEE_MISMATCH / AMOUNT_MISMATCH / MISSING_SETTLEMENT / MISSING_BANK_TRANSACTION / DELAYED_SETTLEMENT / DUPLICATE_SETTLEMENT / BANK_REFERENCE_MISMATCH`，以及「部分对账（partial）」；设计原则是「匹配由确定性规则完成，LLM 只解释异常原因并给出建议动作」。该仓库 GitHub API 未显示许可证（2026-11-02 查询），所以**不得复制其代码**。
  - https://github.com/Aoun-source/ledgerpilot-ai ——AMD Developer Hackathon 作品（MIT），应付账款三方匹配；README 写明「读不出或缺失的值进入人工复核（hold），绝不猜测」「数字全部由代码算」「模型可以让一个案例更严格，但不能更宽松」「每笔付款都要人点同意」。
  - 以上内容来自两个仓库的 README（2026-11-02 读取），其代码实现、评测数字均「未核实」。

## 范围
写 `docs/rules/recon-categories.md`，包含：
1. **分类总表**：实施方案 6.1 现有 13 个原因码 + 下面的候选新码，每个写：中文名、触发条件（精确到字段）、严重度（info/warn/error）、是否影响匹配率分母、人话模板（含 `{order_id}` 等占位符）、建议处理动作、对应合成样本场景（T08 anomalies.json）。
2. **候选新原因码**（标注「候选，待 maken 确认」，确认前不进 `IssueKind` 枚举）：
   | 候选码 | 借鉴自 | 用途 |
   |---|---|---|
   | `FEE_OVERCHARGE` | Varun 仓库的 FEE_MISMATCH 思路 | 平台费用高于用户提供的参考费率（`fee_reference`），匹配仍算成功 |
   | `SETTLEMENT_DELAYED` / 状态「待下期」 | DELAYED_SETTLEMENT 思路 | 订单在 GRACE_DAYS 内未结算，只提示不报错（与 `NOT_IN_SETTLEMENT` 的边界写清楚） |
   | `CHARGEBACK` | 本项目 T08 场景 | 拒付单独统计（目前按退款计入利润） |
   | `PARTIAL_REFUND` | 本项目 T08 场景 | 是否需要单独提示（推断：只做 info） |
   | `DUPLICATE_SETTLEMENT` | DUPLICATE_SETTLEMENT 思路 | 同一订单在两个结算里都出现收款 |
3. **匹配状态**：`matched` / `partial`（实施方案 4 `match.status` 已有）/ 未匹配（必有 issue）三态的定义；「partial」的判定条件。
4. **确定性规则 vs AI 的分工**：规则判定原因码；AI（v0.5）只写解释草稿和建议，用户确认；AI 只能把状态改得更严（例如建议人工复核），不能把异常关掉（借鉴 Aoun 仓库思路）。
5. **置信度 / 自动处理**：v0.1 不做任何自动关闭异常；记录为以后的设计问题（推断：v0.5 可考虑「高置信度建议 → 仍需人工确认」）。
6. **开放问题清单**：给 maken 勾选的问题（如：多收费阈值用绝对值还是百分比？拒付要不要单独一行利润？）。

同时在 `core/enums.py` 旁边新建 `src/crosserp/issues/catalog_draft.yaml`（每个码的中文人话模板草稿），W3 的 issues 模块会读它；**不改 `IssueKind` 枚举**。

## 不做
- 不写对账代码。不 clone、不 vendor 上述仓库。

## 步骤
1. 读实施方案 6.1/6.2 和 T08 的场景表。
2. 打开上面两个 README 核对引用内容（若打不开，在文档里标「未核实」并跳过对应借鉴点）。
3. 写文档和 YAML 草稿；每个借鉴点附链接。
4. `tests/unit/test_issue_catalog.py`：YAML 中每个正式原因码都存在于 `IssueKind`，每个模板占位符格式合法。

## 涉及文件
`docs/rules/recon-categories.md` `src/crosserp/issues/catalog_draft.yaml` `tests/unit/test_issue_catalog.py` `CHANGELOG.md`

## 验收标准
| 命令 | 期望 |
|---|---|
| `uv run pytest tests/unit/test_issue_catalog.py -q` | passed |
| `grep -c "github.com/" docs/rules/recon-categories.md` | ≥2（借鉴来源都有链接） |

## maken 人工验收清单
- [ ] 读 `docs/rules/recon-categories.md` 的分类总表，每一行问自己：「我的会计/运营看到这句人话能懂吗？」
- [ ] 在「候选新原因码」表里，逐个写「要 / 不要 / 以后再说」。
- [ ] 回答「开放问题清单」，把答案写在文档末尾或发给代理。

## 问题

## 完成记录
