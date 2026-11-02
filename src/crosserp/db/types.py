"""三库金额、汇率和时间类型。

SQLite 的 NUMERIC 会把小数收成整数或浮点。Money4 在 SQLite 上存整数万分位。业务代码只看到 Decimal。
超过允许小数位直接报错。不舍入。
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import BigInteger, DateTime, Numeric, String
from sqlalchemy.engine import Dialect
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import TypeDecorator

from crosserp.core.errors import PrecisionError

_MONEY_QUANTUM = Decimal("0.0001")
_FX_QUANTUM = Decimal("0.00000001")
_MONEY4_MAX = Decimal("999999999999999.9999")
# SQLite INTEGER 是有符号 64 位。任务规定万分位上限取对称值。不使用多出来的一个负数。
_SQLITE_MONEY4_MAX = Decimal("922337203685477.5807")
_FX_MAX = Decimal("9999999999.99999999")
_FX_TEXT_LIMIT = 32


def _require_decimal(value: object, label: str) -> Decimal:
    if isinstance(value, float):
        raise TypeError(f"禁止 float。{label} 必须是 Decimal")
    if not isinstance(value, Decimal):
        raise TypeError(f"{label} 必须是 Decimal")
    if not value.is_finite():
        raise PrecisionError(f"{label} 必须是有限 Decimal")
    return value


def _reject_extra_places(value: Decimal, quantum: Decimal, label: str) -> None:
    try:
        quantized = value.quantize(quantum)
    except InvalidOperation as exc:
        raise PrecisionError(f"{label} 超出允许精度") from exc
    if quantized != value:
        exponent = quantum.as_tuple().exponent
        places = -exponent if isinstance(exponent, int) else 0
        raise PrecisionError(f"{label} 小数位超过 {places} 位。拒绝舍入")


def _quantize_result(value: Decimal, quantum: Decimal) -> Decimal:
    quantized = value.quantize(quantum)
    if quantized == 0:
        return Decimal(0).quantize(quantum)
    return quantized


class Money4(TypeDecorator[Decimal]):
    """DECIMAL(19,4)。SQLite 存整数万分位。"""

    impl = Numeric(19, 4, asdecimal=True)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "sqlite":
            return dialect.type_descriptor(BigInteger())
        return dialect.type_descriptor(Numeric(19, 4, asdecimal=True))

    def process_bind_param(self, value: Decimal | None, dialect: Dialect) -> Decimal | int | None:
        if value is None:
            return None
        decimal_value = _require_decimal(value, "金额")
        _reject_extra_places(decimal_value, _MONEY_QUANTUM, "金额")
        if abs(decimal_value) > _MONEY4_MAX:
            raise PrecisionError("金额超出 DECIMAL(19,4) 范围 ±999999999999999.9999")
        if dialect.name == "sqlite":
            if abs(decimal_value) > _SQLITE_MONEY4_MAX:
                raise PrecisionError("金额超出 SQLite 万分位整数范围 ±922337203685477.5807")
            # 小数位已限制在 4 位。乘 10000 后是整数。
            return int(decimal_value * 10000)
        return decimal_value

    def process_result_value(self, value: object, dialect: Dialect) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, float):
            raise TypeError("禁止 float。金额读出不能是 float")
        if dialect.name == "sqlite":
            if isinstance(value, bool) or not isinstance(value, int | Decimal | str):
                raise TypeError("SQLite 金额读出类型无法识别")
            decimal_value = Decimal(value).scaleb(-4)
        else:
            if isinstance(value, bool) or not isinstance(value, Decimal | int | str):
                raise TypeError("金额读出类型无法识别")
            decimal_value = Decimal(value)
        return _quantize_result(decimal_value, _MONEY_QUANTUM)


class FxRate(TypeDecorator[Decimal]):
    """DECIMAL(18,8)。SQLite 存 Decimal 的固定小数字符串。长度不超过 32。"""

    impl = Numeric(18, 8, asdecimal=True)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "sqlite":
            return dialect.type_descriptor(String(32))
        return dialect.type_descriptor(Numeric(18, 8, asdecimal=True))

    def process_bind_param(self, value: Decimal | None, dialect: Dialect) -> Decimal | str | None:
        if value is None:
            return None
        decimal_value = _require_decimal(value, "汇率")
        _reject_extra_places(decimal_value, _FX_QUANTUM, "汇率")
        if abs(decimal_value) > _FX_MAX:
            raise PrecisionError("汇率超出 DECIMAL(18,8) 范围 ±9999999999.99999999")
        if dialect.name == "sqlite":
            rendered = format(decimal_value, "f")
            if len(rendered) > _FX_TEXT_LIMIT:
                raise PrecisionError("汇率字符串超过 SQLite String(32)")
            return rendered
        return decimal_value

    def process_result_value(self, value: object, dialect: Dialect) -> Decimal | None:
        del dialect
        if value is None:
            return None
        if isinstance(value, float):
            raise TypeError("禁止 float。汇率读出不能是 float")
        if isinstance(value, bool) or not isinstance(value, Decimal | int | str):
            raise TypeError("汇率读出类型无法识别")
        return _quantize_result(Decimal(value), _FX_QUANTUM)


class UtcDateTime(TypeDecorator[datetime]):
    """写入必须带时区。转成 UTC 后存储。读出一律是 UTC。

    MySQL DATETIME 和 SQLite 不存时区。因此存 naive UTC。PostgreSQL 用 timestamptz。
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(DateTime(timezone=True))
        if dialect.name == "mysql":
            # fsp=6 避免 MySQL DATETIME 默认丢掉微秒。仍是无时区的 UTC。
            from sqlalchemy.dialects.mysql import DATETIME

            return dialect.type_descriptor(DATETIME(fsp=6))
        return dialect.type_descriptor(DateTime(timezone=False))

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError("时间必须是 datetime")
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("时间必须带时区")
        utc_value = value.astimezone(UTC)
        if dialect.name == "postgresql":
            return utc_value
        return utc_value.replace(tzinfo=None)

    def process_result_value(self, value: object, dialect: Dialect) -> datetime | None:
        del dialect
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError("时间读出类型无法识别")
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
