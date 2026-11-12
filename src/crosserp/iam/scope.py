"""店铺数据范围的显式结果和应用到查询的唯一函数。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import false

if TYPE_CHECKING:
    from crosserp.api.errors import APIError

# 08/02 第 13 节的范围维度。店铺 id 只认代码和测试里真实使用的 storeIds。
_OTHER_SCOPE_TYPES = frozenset({"department", "self", "owner", "warehouse", "amount"})
_STORE_SCOPE_TYPES = frozenset({"storeIds", "all"})
_KNOWN_SCOPE_TYPES = _STORE_SCOPE_TYPES | _OTHER_SCOPE_TYPES


@dataclass(frozen=True, slots=True)
class AllStores:
    """角色或数据范围规则明确给出的全部店铺。"""


StoreScope = AllStores | frozenset[UUID]


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


def _has_store_rule(rules: Sequence[tuple[str, Any]]) -> bool:
    return any(scope_type in _STORE_SCOPE_TYPES for scope_type, _values in rules)


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


def _invalid(message: str) -> APIError:
    from crosserp.api.errors import APIError, ErrorCode

    return APIError(ErrorCode.VALIDATION_FAILED, message)


__all__ = ["AllStores", "StoreScope", "apply_store_scope", "resolve_store_scope"]
