# T03 金额核心：Money + parse_amount

> **当前状态：已完成；现行依据见 [backend-phases.md](backend-phases.md) 与 [08-后端模块与 API 设计](../../design/08-后端模块与API设计.md)。**

| 状态 | 周 | 估时 | 依赖 | 分支 |
|---|---|---|---|---|
| review | W1 | 1 天 | T01 | `task/T03-core-money` |

## 目标
全项目唯一的金额类型和金额解析函数，保证「钱永远是 Decimal，不会丢精度」。

## 背景
- 实施方案 4（金额规则）、5.1（EU 站 `95,00`）、7.2（禁止 float）、8 W1 第 2 条。

## 范围
- `core/money.py`：
  - `@dataclass(frozen=True) class Money: amount: Decimal; currency: str`（currency 是 3 位大写 ISO 代码，构造时校验）。
  - 支持 `+`、`-`、取负、`sum()`（提供 `Money.zero(ccy)` 或 `money_sum(items, ccy)`）、与整数/Decimal 相乘（数量 × 单价）。
  - 不同币种相加/相减 → 抛 `CurrencyMismatchError`。
  - 构造时传 float → 抛 `TypeError`。
  - `quantize_display() -> Decimal`：`ROUND_HALF_UP` 到 2 位，只用于展示。
  - `parse_amount(text: str, locale: Literal["us","eu"]) -> Decimal`：
    - us：`"1,234.56"` `"-12.30"` `"1234"` `"(12.30)"`（括号负数，推断，需在测试中注明）
    - eu：`"1.234,56"` `"95,00"` `"-0,50"`
    - 去掉首尾空白和不换行空格；空字符串 → 抛 `AmountParseError`；无法解析 → `AmountParseError`（带原文）。
  - `locale_for(marketplace: str | None, currency: str) -> Literal["us","eu"]`：EUR 及 Amazon.de/.fr/.it/.es/.nl 等 → `"eu"`，其他 → `"us"`；映射表写成模块常量并注明「待真实数据验证」。
- `core/errors.py`：`CrossErpError` 基类、`CurrencyMismatchError`、`AmountParseError`、`PrecisionError`。
- `tests/guard/test_no_float.py`：AST 扫描 `src/crosserp/`，出现 `float(` 调用即失败（允许用 `# noqa: money-float` 注释白名单，目前应为 0 处）。

## 不做
- 不做汇率换算（那是 profit 模块，W3）。不做数据库类型（T04）。

## 步骤
1. 写 errors.py、money.py，全部类型注解，通过 `mypy --strict`。
2. 单元测试 `tests/unit/test_money.py`：上面每个例子至少 1 条，含异常路径。
3. 性质测试 `tests/property/test_money_props.py`（hypothesis）：
   - `Decimal` 用 `st.decimals(min_value=-10**12, max_value=10**12, places=4, allow_nan=False, allow_infinity=False)`；
   - a+b-b == a；加法交换律、结合律；sum 结果与逐项相加一致；
   - `parse_amount(format_us(x), "us") == x` 与 `parse_amount(format_eu(x), "eu") == x` 往返（format 函数写在测试里）。
4. 写 guard 测试。

## 涉及文件
`src/crosserp/core/money.py` `src/crosserp/core/errors.py` `tests/unit/test_money.py` `tests/property/test_money_props.py` `tests/guard/test_no_float.py` `CHANGELOG.md`

## 验收标准
| 命令 | 期望 |
|---|---|
| `uv run python -c "from decimal import Decimal; from crosserp.core.money import parse_amount; assert parse_amount('95,00','eu')==Decimal('95.00'); assert parse_amount('1.234,56','eu')==Decimal('1234.56'); assert parse_amount('1,234.56','us')==Decimal('1234.56'); print('ok')"` | 输出 `ok` |
| `uv run pytest tests/unit/test_money.py tests/property tests/guard -q` | 全部 passed |
| `uv run mypy` | 无错误 |

## maken 人工验收清单
- [ ] 复制上面第一条命令到 PowerShell 运行，看到 `ok`。
- [ ] 运行 `uv run pytest -q`，全部通过。
- [ ] 随便打开 `money.py`，搜索 `float`，除了「禁止 float」的报错说明外不应出现。

## 问题
无阻塞问题。EU 站点映射只收录任务列出的 Amazon.de / .fr / .it / .es / .nl，未猜测 Amazon.pl / .se / .com.be。待真实数据验证。币种为 EUR 时仍返回 `eu`。

## 完成记录
当前分支 `main`（按本次指令提交到当前分支，未另开 `task/T03-core-money`）。未推送。未把状态改成 done。

2026-11-02 在本 worktree 实际运行。解释器 `D:\make\write\work\CrossERP\.venv\Scripts\python.exe`，Python 3.14.10。未使用 `uv run`。`PYTHONPATH` 指向本 worktree 的 `src`。导入文件为 `src\crosserp\core\money.py`。

| 命令 | 结果 |
|---|---|
| `python -c "from decimal import Decimal; from crosserp.core.money import parse_amount; assert parse_amount('95,00','eu')==Decimal('95.00'); assert parse_amount('1.234,56','eu')==Decimal('1234.56'); assert parse_amount('1,234.56','us')==Decimal('1234.56'); print('ok')"` | 退出码 0。输出 `ok` |
| `python -m pytest tests/unit/test_money.py tests/property tests/guard -q` | 退出码 0。`23 passed in 1.05s` |
| `mypy` | 退出码 0。`Success: no issues found in 13 source files` |
| `python -m pytest -q` | 退出码 0。`24 passed in 0.78s` |
| `ruff format --check .` | 退出码 0。`20 files already formatted` |
| `ruff check .` | 退出码 0。`All checks passed!` |

`money.py` 中的 `float` 只出现在「禁止 float」说明和 `isinstance(..., float)` 拒绝路径，没有 `float()` 调用。guard 扫描 `src/crosserp/`，`# noqa: money-float` 为 0 处。
