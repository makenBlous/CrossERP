# T25 v0.1 验收：指标 2、3 + 基础安装 + 三库，汇总证据【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】

> **当前状态：部分；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W3 | 0.5 天 | T16, T21, T24 | `task/T25-v01-acceptance` |

## 目标
发布 v0.1 之前，把每一项验收标准的结果和证据链接写进一个文件，maken 看这一个文件就能决定「能不能发」。

## 背景
- 实施方案 8 W3 验收：100+ 订单匹配率 ≥95%；利润与 maken 手算一致；`uv tool install` + `demo` 三系统可用。
- 「指标 × 版本 × 证据」表 v0.1 列：指标 1「基础能装」、指标 2（匹配 ≥95% + 100% 有原因，证据：golden 测试断言 + 报表）、指标 3（利润误差 0，证据：golden 测试）；新增验收项 A（三库，待 maken 确认的新增项）。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
- 指标 4–7 不在 v0.1 范围。

## 范围
- `docs/evidence/v0.1-acceptance.md`，一项一行：

  | 项 | 标准 | 结果 | 证据 | 状态 |
  |---|---|---|---|---|
  | 指标 2 合成 | 每店铺匹配率 ≥95%，未匹配 100% 有原因 | 实际数字 | CI 运行链接 + `tests/golden` | 通过/未通过 |
  | 指标 2 真实 | 同上（maken 的脱敏数据，≥100 笔订单） | 实际数字 | `docs/eval-results/v0.1-golden-real.md`（只放汇总数字，不放原始数据） | |
  | 指标 3 合成 | golden 逐分一致 | N/N | CI 链接 | |
  | 指标 3 真实 | maken 手算 20 个 SKU 逐分一致 | n/20 | 同上 | |
  | 指标 1 基础 | 三系统 `uv tool install` + `demo --check` 通过 | 各系统耗时 | CI `install-smoke` 链接 + maken 实测耗时 | |
  | A 三库 | SQLite/MySQL 8.4/PG 18 同一套测试全绿 | 测试数 | CI `db-matrix` 链接 | |【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
  | 覆盖率 | ≥60%（v0.1 门槛） | 实际 % | CI 链接 | |
  | 未决口径 | T15/T17/T19/T20 里 maken 还没答复的问题 | 列表 | 各任务「问题」节 | |

- 真实数据项如果 maken 还没准备好：状态写「未验收（缺真实数据）」，**不要**用合成结果顶替。
- 在 `CHANGELOG.md` 写好 `## [0.1.0] - 未发布` 小节（新增功能、已知限制：未含广告、非订单费用未分摊、拒付/退货口径待真实数据验证等）。

## 不做
- 不打 tag、不发布（T26，由 maken 操作）。
- 不改任何业务代码；发现问题 → 在对应任务开 issue/写「问题」，本任务 blocked。

## 步骤
1. 拉取 main 最新 CI 结果，逐项填表，链接用具体运行的 URL。
2. 本地再跑一遍 `uv run crosserp demo --check` 和 `uv run pytest --cov=crosserp --cov-fail-under=60`，输出摘要贴进完成记录。

## 涉及文件
`docs/evidence/v0.1-acceptance.md` `CHANGELOG.md`

## 验收标准（代理自测，全部要实际跑）
| 命令 / 检查 | 期望 |
|---|---|
| `uv run crosserp demo --check` | 退出码 0 |
| `uv run pytest --cov=crosserp --cov-fail-under=60` | passed |
| `docs/evidence/v0.1-acceptance.md` | 每行都有证据链接或明确写「未验收 + 原因」 |

## maken 人工验收清单
- [ ] 读 `docs/evidence/v0.1-acceptance.md`，逐个点开证据链接。
- [ ] 「指标 2 真实」「指标 3 真实」两行必须是你自己跑出来的数字（T21 清单）。
- [ ] 全部「通过」→ 在本文件完成记录里写「同意发布 v0.1.0」，再做 T26。

## 问题

## 完成记录

- 完成内容：新增 `docs/evidence/v0.1-acceptance.md`，汇总指标 1/2/3、三库和覆盖率证据；补充 `CHANGELOG.md` 的 `[0.1.0] - 未发布` 小节。【历史验收口径；现行正式目标为 MySQL 8.4，SQLite 仅演示，PostgreSQL 仅备选】
- 测试结果：本地 `.venv` `crosserp demo --check --no-browser` 通过；SQLite 全量 `204 passed, 2 skipped`，覆盖率 `86.24%`；MySQL 8.4/PG18 定向验证通过；真实数据两项明确标注未验收，不用合成数据代替。
- 未决事项：GitHub Actions 具体运行链接和 maken 的真实 20 SKU 手算验收仍待人工完成；本任务不替 maken 同意发布。
