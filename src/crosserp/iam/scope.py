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

# 店铺 id 认 storeIds、all、ownedStores。期间和法人是财务范围的另外两维。
STORE_SCOPE_TYPES = frozenset({"storeIds", "all", "ownedStores"})
UNIMPLEMENTED_SCOPE_TYPES = frozenset(
    {
        "department",
        "self",
        "owner",
        "warehouse",
        "amount",
        "skuCategory",
        "employees",
        "paymentAccount",
        "purchaseOrder",
    }
)
OTHER_KNOWN_SCOPE_TYPES = frozenset({"periods", "legalEntities"})
KNOWN_SCOPE_TYPES = STORE_SCOPE_TYPES | UNIMPLEMENTED_SCOPE_TYPES | OTHER_KNOWN_SCOPE_TYPES
ScopeRule = tuple[str, Any]
_PERIOD_SCOPE_TYPES = frozenset({"periods", "all"})
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
    role_rules: Sequence[ScopeRule],
    global_rules: Sequence[ScopeRule],
    owned_store_ids: frozenset[UUID],
    allow_tokens: set[str],
    deny_tokens: set[str],
    apply_agent_narrowing: bool,
    agent_store_ids: frozenset[UUID],
    universe_store_ids: frozenset[UUID],
) -> StoreScope:
    """角色规则并集后应用用户例外再与 AI 收窄取交集。

    role_id 为空的全局规则与角色结果取交集。缺规则或格式不对时拒绝。
    未实现维度贡献空集。
    """
    _reject_unknown([*role_rules, *global_rules])
    _reject_unknown_tokens(role_tokens | allow_tokens | deny_tokens)
    role_scope = _role_union(role_tokens, role_rules, owned_store_ids)
    global_scope = _listed_scope(global_rules, owned_store_ids)
    if role_scope is None and global_scope is None and not allow_tokens:
        raise _invalid("店铺数据范围规则缺失")
    base = _combine_role_and_global(role_scope, global_scope)
    expanded = _union(base, _token_scope(allow_tokens, owned_store_ids))
    narrowed = _subtract(
        expanded,
        _token_scope(deny_tokens, owned_store_ids),
        universe_store_ids,
    )
    if apply_agent_narrowing:
        return _intersect(narrowed, agent_store_ids)
    return narrowed


def choose_entity_rules(rows: Sequence[tuple[str, str, Any]], entity: str) -> list[ScopeRule]:
    """实体上已有店铺规则时用实体规则。否则用通配规则。"""
    entity_rows = [
        (scope_type, values) for row_entity, scope_type, values in rows if row_entity == entity
    ]
    if any(scope_type in STORE_SCOPE_TYPES for scope_type, _values in entity_rows):
        return entity_rows
    return [(scope_type, values) for row_entity, scope_type, values in rows if row_entity == "*"]


def _combine_role_and_global(
    role_scope: StoreScope | None, global_scope: StoreScope | None
) -> StoreScope:
    if role_scope is None:
        if global_scope is None:
            return frozenset()
        return global_scope
    if global_scope is None:
        return role_scope
    return _intersect(role_scope, global_scope)


def _role_union(
    tokens: set[str],
    rules: Sequence[ScopeRule],
    owned_store_ids: frozenset[UUID],
) -> StoreScope | None:
    if not tokens and not rules:
        return None
    if "all" in tokens or any(scope_type == "all" for scope_type, _values in rules):
        _assert_all_values([values for scope_type, values in rules if scope_type == "all"])
        return AllStores()
    if _has_store_contribution(tokens, rules):
        return frozenset(_collect_store_ids(tokens, rules, owned_store_ids))
    if _only_unimplemented(tokens, rules):
        return frozenset()
    raise _invalid("店铺数据范围规则缺失")


def _listed_scope(
    rules: Sequence[ScopeRule], owned_store_ids: frozenset[UUID]
) -> StoreScope | None:
    if not rules:
        return None
    store_rules = [values for scope_type, values in rules if scope_type == "storeIds"]
    all_rules = [values for scope_type, values in rules if scope_type == "all"]
    if store_rules and all_rules:
        _assert_all_values(all_rules)
        return AllStores()
    if store_rules:
        parsed: set[UUID] = set()
        for values in store_rules:
            parsed.update(_parse_store_ids(values))
        return frozenset(parsed)
    if all_rules:
        _assert_all_values(all_rules)
        return AllStores()
    if any(scope_type == "ownedStores" for scope_type, _values in rules):
        return frozenset(owned_store_ids)
    if _only_unimplemented(set(), rules):
        return None
    raise _invalid("店铺数据范围规则缺失")


def _has_store_contribution(tokens: set[str], rules: Sequence[ScopeRule]) -> bool:
    if "ownedStores" in tokens or any(token.startswith("store:") for token in tokens):
        return True
    return any(scope_type in {"storeIds", "ownedStores"} for scope_type, _values in rules)


def _only_unimplemented(tokens: set[str], rules: Sequence[ScopeRule]) -> bool:
    tokens_known = all(token in UNIMPLEMENTED_SCOPE_TYPES for token in tokens)
    rules_known = all(scope_type in UNIMPLEMENTED_SCOPE_TYPES for scope_type, _values in rules)
    return tokens_known and rules_known and bool(tokens or rules)


def _collect_store_ids(
    tokens: set[str],
    rules: Sequence[ScopeRule],
    owned_store_ids: frozenset[UUID],
) -> set[UUID]:
    store_ids: set[UUID] = set()
    if "ownedStores" in tokens or any(scope_type == "ownedStores" for scope_type, _values in rules):
        store_ids.update(owned_store_ids)
    for scope_type, values in rules:
        if scope_type == "storeIds":
            store_ids.update(_parse_store_ids(values))
    for token in tokens:
        if token.startswith("store:"):
            store_ids.add(_parse_store_token(token))
    return store_ids


def _token_scope(tokens: set[str], owned_store_ids: frozenset[UUID]) -> StoreScope:
    if not tokens:
        return frozenset()
    if "all" in tokens:
        return AllStores()
    if _only_unimplemented(tokens, []):
        return frozenset()
    if not _has_store_contribution(tokens, []):
        raise _invalid("店铺数据范围规则缺失")
    return frozenset(_collect_store_ids(tokens, [], owned_store_ids))


def _union(left: StoreScope, right: StoreScope) -> StoreScope:
    if isinstance(left, AllStores) or isinstance(right, AllStores):
        if (isinstance(left, AllStores) and not right) or (
            isinstance(right, AllStores) and not left
        ):
            return left if isinstance(left, AllStores) else right
        return AllStores()
    return frozenset(left) | frozenset(right)


def _intersect(left: StoreScope, right: StoreScope | frozenset[UUID]) -> StoreScope:
    if isinstance(right, AllStores):
        return left
    if isinstance(left, AllStores):
        return frozenset(right)
    return frozenset(left) & frozenset(right)


def _subtract(
    scope: StoreScope, removed: StoreScope, universe_store_ids: frozenset[UUID]
) -> StoreScope:
    if isinstance(removed, AllStores):
        return frozenset()
    if not removed:
        return scope
    if isinstance(scope, AllStores):
        return universe_store_ids - removed
    return frozenset(scope) - removed


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


def _has_period_rule(rules: Sequence[tuple[str, Any]]) -> bool:
    return any(scope_type in _PERIOD_SCOPE_TYPES for scope_type, _values in rules)


def _has_legal_rule(rules: Sequence[tuple[str, Any]]) -> bool:
    return any(scope_type in {"legalEntities", "all"} for scope_type, _values in rules)


def _reject_unknown(rules: Sequence[ScopeRule]) -> None:
    for scope_type, _values in rules:
        if scope_type not in KNOWN_SCOPE_TYPES:
            raise _invalid(f"店铺范围规则格式无效: {scope_type}")


def _reject_unknown_tokens(tokens: set[str]) -> None:
    for token in tokens:
        if token.startswith("store:"):
            _parse_store_token(token)
            continue
        if token not in KNOWN_SCOPE_TYPES:
            raise _invalid(f"角色数据范围格式无效: {token}")


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


def _parse_store_token(token: str) -> UUID:
    try:
        return UUID(token.removeprefix("store:"))
    except ValueError as exc:
        raise _invalid("店铺范围 store 令牌含无效 UUID") from exc


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
    "KNOWN_SCOPE_TYPES",
    "STORE_SCOPE_TYPES",
    "UNIMPLEMENTED_SCOPE_TYPES",
    "AllLegalEntities",
    "AllPeriods",
    "AllStores",
    "LegalEntityScope",
    "PeriodScope",
    "StoreScope",
    "apply_period_scope",
    "apply_store_scope",
    "choose_entity_rules",
    "legal_entity_contains",
    "period_contains",
    "resolve_legal_entity_scope",
    "resolve_period_scope",
    "resolve_store_scope",
    "store_contains",
]
