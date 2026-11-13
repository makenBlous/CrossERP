"""店铺数据范围的显式结果和应用到查询的唯一函数。"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import false

if TYPE_CHECKING:
    from crosserp.api.errors import APIError

# 08/02 第 13 节的范围维度。店铺 id 只认代码和测试里真实使用的 storeIds。
# 期间是对账范围的第二维。规则类型 periods 与 storeIds 分开解析。
_OTHER_SCOPE_TYPES = frozenset(
    {"department", "self", "owner", "warehouse", "amount", "periods", "legalEntities"}
)
_STORE_SCOPE_TYPES = frozenset({"storeIds", "all"})
_PERIOD_SCOPE_TYPES = frozenset({"periods", "all"})
_KNOWN_SCOPE_TYPES = _STORE_SCOPE_TYPES | _OTHER_SCOPE_TYPES
_PERIOD_TEXT = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@dataclass(frozen=True, slots=True)
class AllStores:
    """角色或数据范围规则明确给出的全部店铺。"""


StoreScope = AllStores | frozenset[UUID]


@dataclass(frozen=True, slots=True)
class AllPeriods:
    """角色或数据范围规则明确给出的全部期间。"""


PeriodScope = AllPeriods | frozenset[str]


@dataclass(frozen=True, slots=True)
class AllLegalEntities:
    """角色或数据范围规则明确给出的全部法人。"""


LegalEntityScope = AllLegalEntities | frozenset[str]


def store_contains(scope: StoreScope, store_id: UUID) -> bool:
    """单条记录是否落在店铺范围内。空集为否。"""
    if isinstance(scope, AllStores):
        return True
    return store_id in scope


def apply_store_scope(statement: Any, column: Any, scope: StoreScope) -> Any:
    """把店铺范围应用到语句。空集生成恒假条件。"""
    if isinstance(scope, AllStores):
        return statement
    if not scope:
        return statement.where(false())
    return statement.where(column.in_(scope))


def resolve_store_scope(
    role_tokens: set[str],
    *,
    entity_rules: Sequence[tuple[str, Any]],
    wildcard_rules: Sequence[tuple[str, Any]],
) -> StoreScope:
    """按角色并集和 IamDataScopeRule 解析店铺范围。缺失或格式不对时拒绝放行。"""
    for token in role_tokens:
        if token != "all":
            raise _invalid(f"角色数据范围格式无效: {token}")
    _reject_unknown([*entity_rules, *wildcard_rules])
    selected = entity_rules if _has_store_rule(entity_rules) else wildcard_rules
    store_rules = [values for scope_type, values in selected if scope_type == "storeIds"]
    all_rules = [values for scope_type, values in selected if scope_type == "all"]
    if store_rules:
        store_ids: set[UUID] = set()
        for values in store_rules:
            store_ids.update(_parse_store_ids(values))
        if all_rules:
            _assert_all_values(all_rules)
            return AllStores()
        return frozenset(store_ids)
    if all_rules or "all" in role_tokens:
        _assert_all_values(all_rules)
        return AllStores()
    raise _invalid("店铺数据范围规则缺失")


def period_contains(scope: PeriodScope, period: str) -> bool:
    """单条记录是否落在期间范围内。空集为否。"""
    if isinstance(scope, AllPeriods):
        return True
    return period in scope


def apply_period_scope(statement: Any, column: Any, scope: PeriodScope) -> Any:
    """把期间范围应用到语句。空集生成恒假条件。"""
    if isinstance(scope, AllPeriods):
        return statement
    if not scope:
        return statement.where(false())
    return statement.where(column.in_(scope))


def resolve_period_scope(
    role_tokens: set[str],
    *,
    entity_rules: Sequence[tuple[str, Any]],
    wildcard_rules: Sequence[tuple[str, Any]],
) -> PeriodScope:
    """按角色并集和 IamDataScopeRule 解析期间范围。格式不对时拒绝放行。"""
    for token in role_tokens:
        if token != "all":
            raise _invalid(f"角色数据范围格式无效: {token}")
    _reject_unknown([*entity_rules, *wildcard_rules])
    selected = entity_rules if _has_period_rule(entity_rules) else wildcard_rules
    period_rules = [values for scope_type, values in selected if scope_type == "periods"]
    all_rules = [values for scope_type, values in selected if scope_type == "all"]
    if period_rules:
        periods: set[str] = set()
        for values in period_rules:
            periods.update(_parse_periods(values))
        if all_rules:
            _assert_all_values(all_rules)
            return AllPeriods()
        return frozenset(periods)
    if all_rules or "all" in role_tokens:
        _assert_all_values(all_rules)
        return AllPeriods()
    return frozenset()


def legal_entity_contains(scope: LegalEntityScope, legal_entity: str | None) -> bool:
    """单条记录是否落在法人范围内。空集或缺失法人为否。"""
    if isinstance(scope, AllLegalEntities):
        return True
    if legal_entity is None:
        return False
    return legal_entity in scope


def resolve_legal_entity_scope(
    role_tokens: set[str],
    *,
    entity_rules: Sequence[tuple[str, Any]],
    wildcard_rules: Sequence[tuple[str, Any]],
) -> LegalEntityScope:
    """按角色并集和 IamDataScopeRule 解析法人范围。格式不对时拒绝放行。"""
    for token in role_tokens:
        if token != "all":
            raise _invalid(f"角色数据范围格式无效: {token}")
    _reject_unknown([*entity_rules, *wildcard_rules])
    selected = entity_rules if _has_legal_rule(entity_rules) else wildcard_rules
    legal_rules = [values for scope_type, values in selected if scope_type == "legalEntities"]
    all_rules = [values for scope_type, values in selected if scope_type == "all"]
    if legal_rules:
        names: set[str] = set()
        for values in legal_rules:
            names.update(_parse_legal_entities(values))
        if all_rules:
            _assert_all_values(all_rules)
            return AllLegalEntities()
        return frozenset(names)
    if all_rules or "all" in role_tokens:
        _assert_all_values(all_rules)
        return AllLegalEntities()
    return frozenset()


def _has_store_rule(rules: Sequence[tuple[str, Any]]) -> bool:
    return any(scope_type in _STORE_SCOPE_TYPES for scope_type, _values in rules)


def _has_period_rule(rules: Sequence[tuple[str, Any]]) -> bool:
    return any(scope_type in _PERIOD_SCOPE_TYPES for scope_type, _values in rules)


def _has_legal_rule(rules: Sequence[tuple[str, Any]]) -> bool:
    return any(scope_type in {"legalEntities", "all"} for scope_type, _values in rules)


def _reject_unknown(rules: Sequence[tuple[str, Any]]) -> None:
    for scope_type, _values in rules:
        if scope_type not in _KNOWN_SCOPE_TYPES:
            raise _invalid(f"店铺范围规则格式无效: {scope_type}")


def _assert_all_values(values_list: Sequence[Any]) -> None:
    for values in values_list:
        if not isinstance(values, list):
            raise _invalid("店铺范围 all 的 values 必须是数组")


def _parse_store_ids(values: Any) -> frozenset[UUID]:
    if not isinstance(values, list):
        raise _invalid("店铺范围 storeIds 必须是数组")
    parsed: set[UUID] = set()
    for item in values:
        if not isinstance(item, str):
            raise _invalid("店铺范围 storeIds 必须是 UUID 字符串")
        try:
            parsed.add(UUID(item))
        except ValueError as exc:
            raise _invalid("店铺范围 storeIds 含无效 UUID") from exc
    return frozenset(parsed)


def _parse_periods(values: Any) -> frozenset[str]:
    if not isinstance(values, list):
        raise _invalid("期间范围 periods 必须是数组")
    parsed: set[str] = set()
    for item in values:
        if not isinstance(item, str) or _PERIOD_TEXT.fullmatch(item) is None:
            raise _invalid("期间范围 periods 必须是 YYYY-MM")
        parsed.add(item)
    return frozenset(parsed)


def _parse_legal_entities(values: Any) -> frozenset[str]:
    if not isinstance(values, list):
        raise _invalid("法人范围 legalEntities 必须是数组")
    parsed: set[str] = set()
    for item in values:
        if not isinstance(item, str) or item == "":
            raise _invalid("法人范围 legalEntities 必须是非空字符串")
        parsed.add(item)
    return frozenset(parsed)


def _invalid(message: str) -> APIError:
    from crosserp.api.errors import APIError, ErrorCode

    return APIError(ErrorCode.VALIDATION_FAILED, message)


__all__ = [
    "AllLegalEntities",
    "AllPeriods",
    "AllStores",
    "LegalEntityScope",
    "PeriodScope",
    "StoreScope",
    "apply_period_scope",
    "apply_store_scope",
    "legal_entity_contains",
    "period_contains",
    "resolve_legal_entity_scope",
    "resolve_period_scope",
    "resolve_store_scope",
    "store_contains",
]
