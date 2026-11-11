"""JSON API 的公共 Pydantic schema。"""

from __future__ import annotations

from typing import Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator


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


ListingStatus = Literal["active", "inactive"]


class ListingCreateRequest(CamelModel):
    store_id: UUID
    platform_sku: str = Field(min_length=1, max_length=128)
    asin: str | None = Field(default=None, max_length=64)
    price: Money
    status: ListingStatus = "active"


class ListingUpdateRequest(CamelModel):
    status: ListingStatus | None = None
    asin: str | None = Field(default=None, max_length=64)
    price: Money | None = None
    expected_version: StrictInt

    @field_validator("expected_version")
    @classmethod
    def validate_expected_version(cls, value: int) -> int:
        if value < 1:
            raise ValueError("expectedVersion 必须是正整数")
        return value


class ListingStatusRequest(CamelModel):
    ids: list[UUID] = Field(min_length=1)
    status: ListingStatus
    expected_version: StrictInt

    @field_validator("expected_version")
    @classmethod
    def validate_expected_versions(cls, value: int) -> int:
        if value < 1:
            raise ValueError("expectedVersion 必须是正整数")
        return value


T = TypeVar("T")


class Page[T](CamelModel):
    items: list[T]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int


__all__ = [
    "CamelModel",
    "ListingCreateRequest",
    "ListingStatus",
    "ListingStatusRequest",
    "ListingUpdateRequest",
    "Money",
    "Page",
    "PageParams",
    "to_camel",
]
