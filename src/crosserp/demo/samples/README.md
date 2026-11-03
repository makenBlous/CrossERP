# 合成样本

固定种子 `20261109` 生成。金额是 Decimal 合成值。
不是真实卖家数据。也不是亚马逊或 Shopify 的真实费率。

平台取值集中在 `scripts/sample_vocab.py`。每个值都注明「待真实数据验证」。
这不是平台字段全集。仓储费、移除费、FBA 赔偿、促销没有生成。

## 重新生成

在仓库根目录：

```bash
uv run python scripts/gen_samples.py --out samples/synthetic
```

不用 uv 时，把 `src` 放进 `PYTHONPATH`，用项目解释器运行同一脚本。
改生成器后必须重新生成并提交。`EXPECTED.md` 会一起更新。

## 读文件

- csv/tsv 是 UTF-8，无 BOM，行尾 LF。Excel 若中文乱码，用「数据 → 从文本/CSV」并选择 UTF-8。
- `amazon_de_*.tsv` 金额是 `95,00` 这种逗号小数，没有千分位。导入时分隔符选 Tab。
- `orders.csv` 一律用点小数（`amount_locale: us`），币种看 `currency` 列。
- xlsx 的金额单元格是文本，避免写成 float。
- `amazon_us_unbalanced.tsv` 故意不平，不进入匹配率分母。
