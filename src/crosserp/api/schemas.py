"""JSON API 的公共 Pydantic schema。"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail)


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class Money(CamelModel):
    amount_minor: int = Field(alias="amountMinor")
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("amount_minor")
    @classmethod
    def validate_minor(cls, value: int) -> int:
        if value < -(2**63) or value > 2**63 - 1:
            raise ValueError("amountMinor 必须是 int64")
        return value


class PageParams(CamelModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, alias="pageSize", ge=1, le=200)


T = TypeVar("T")


class Page[T](CamelModel):
    items: list[T]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int


__all__ = ["CamelModel", "Money", "Page", "PageParams", "to_camel"]
