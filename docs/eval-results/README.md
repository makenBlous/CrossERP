# Golden 结果

运行 `uv run crosserp check-golden --period 2026-10 --expected tests/golden/profit_expected.csv --report-md docs/eval-results/v0.1-golden-synthetic.md`，会把逐分比对结果写入 Markdown。

合成答案中，实际运行的 SKU 逐行比对；额外的 `reference-only` 行是固定种子的手算参考行，不宣称对应当前样本中的真实 SKU。真实脱敏数据和 maken 的 20 个手算 SKU 放在被 `.gitignore` 忽略的 `samples/real_anonymized/expected/` 下，不提交到仓库。
