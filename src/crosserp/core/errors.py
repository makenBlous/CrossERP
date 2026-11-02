"""领域错误。"""

from __future__ import annotations


class CrossErpError(Exception):
    """CrossERP 业务错误基类。"""


class CurrencyMismatchError(CrossErpError):
    """不同币种不能直接加减。"""

    def __init__(self, left: str, right: str) -> None:
        self.left = left
        self.right = right
        super().__init__(f"币种不一致。{left} 与 {right} 不能直接加减")


class AmountParseError(CrossErpError):
    """金额字符串无法解析。`text` 是调用方传入的原文。"""

    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__(f"无法解析金额 {text!r}")


class PrecisionError(CrossErpError):
    """小数位数或数值范围超出允许精度。T04 的 Money4 / FxRate 使用。"""


class DatabaseConfigError(CrossErpError):
    """数据库配置不满足启动要求。消息用中文说明怎么改。"""
