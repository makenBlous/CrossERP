"""店铺范围解析: 角色并集、用户例外、AI 收窄。"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from crosserp.api.errors import APIError
from crosserp.iam.scope import AllStores, resolve_store_scope


def _ids(*count: int) -> list[UUID]:
    return [uuid4() for _ in range(count[0])]


def test_role_union_includes_inherited_store_ids() -> None:
    first, second = _ids(2)
    scope = resolve_store_scope(
        set(),
        role_rules=[("storeIds", [str(first)]), ("storeIds", [str(second)])],
        global_rules=[],
        owned_store_ids=frozenset(),
        allow_tokens=set(),
        deny_tokens=set(),
        apply_agent_narrowing=False,
        agent_store_ids=frozenset(),
        universe_store_ids=frozenset({first, second}),
    )

    assert scope == frozenset({first, second})


def test_all_in_role_union_wins_over_restricted_role_rules() -> None:
    only = uuid4()
    scope = resolve_store_scope(
        {"all", "ownedStores"},
        role_rules=[("storeIds", [str(only)])],
        global_rules=[],
        owned_store_ids=frozenset({only}),
        allow_tokens=set(),
        deny_tokens=set(),
        apply_agent_narrowing=False,
        agent_store_ids=frozenset(),
        universe_store_ids=frozenset({only}),
    )

    assert scope == AllStores()


def test_global_store_ids_narrow_role_all() -> None:
    visible, hidden = _ids(2)
    scope = resolve_store_scope(
        {"all"},
        role_rules=[],
        global_rules=[("storeIds", [str(visible)])],
        owned_store_ids=frozenset(),
        allow_tokens=set(),
        deny_tokens=set(),
        apply_agent_narrowing=False,
        agent_store_ids=frozenset(),
        universe_store_ids=frozenset({visible, hidden}),
    )

    assert scope == frozenset({visible})


def test_owned_stores_resolve_to_granted_ids_and_empty_is_not_all() -> None:
    owned = uuid4()
    other = uuid4()
    scope = resolve_store_scope(
        {"ownedStores"},
        role_rules=[],
        global_rules=[],
        owned_store_ids=frozenset({owned}),
        allow_tokens=set(),
        deny_tokens=set(),
        apply_agent_narrowing=False,
        agent_store_ids=frozenset(),
        universe_store_ids=frozenset({owned, other}),
    )
    empty = resolve_store_scope(
        {"ownedStores"},
        role_rules=[],
        global_rules=[],
        owned_store_ids=frozenset(),
        allow_tokens=set(),
        deny_tokens=set(),
        apply_agent_narrowing=False,
        agent_store_ids=frozenset(),
        universe_store_ids=frozenset({other}),
    )

    assert scope == frozenset({owned})
    assert empty == frozenset()


def test_unimplemented_dimension_is_empty_not_all() -> None:
    store = uuid4()
    scope = resolve_store_scope(
        {"department"},
        role_rules=[],
        global_rules=[],
        owned_store_ids=frozenset({store}),
        allow_tokens=set(),
        deny_tokens=set(),
        apply_agent_narrowing=False,
        agent_store_ids=frozenset(),
        universe_store_ids=frozenset({store}),
    )

    assert scope == frozenset()


def test_user_exception_allow_adds_and_deny_removes() -> None:
    owned, extra = _ids(2)
    allowed = resolve_store_scope(
        {"ownedStores"},
        role_rules=[],
        global_rules=[],
        owned_store_ids=frozenset({owned}),
        allow_tokens={f"store:{extra}"},
        deny_tokens=set(),
        apply_agent_narrowing=False,
        agent_store_ids=frozenset(),
        universe_store_ids=frozenset({owned, extra}),
    )
    denied = resolve_store_scope(
        {"all"},
        role_rules=[],
        global_rules=[],
        owned_store_ids=frozenset(),
        allow_tokens=set(),
        deny_tokens={f"store:{extra}"},
        apply_agent_narrowing=False,
        agent_store_ids=frozenset(),
        universe_store_ids=frozenset({owned, extra}),
    )

    assert allowed == frozenset({owned, extra})
    assert denied == frozenset({owned})


def test_agent_narrowing_intersects_and_cannot_expand() -> None:
    owned, foreign = _ids(2)
    narrowed = resolve_store_scope(
        {"all"},
        role_rules=[],
        global_rules=[],
        owned_store_ids=frozenset(),
        allow_tokens=set(),
        deny_tokens=set(),
        apply_agent_narrowing=True,
        agent_store_ids=frozenset({owned}),
        universe_store_ids=frozenset({owned, foreign}),
    )
    cannot_expand = resolve_store_scope(
        {"ownedStores"},
        role_rules=[],
        global_rules=[],
        owned_store_ids=frozenset({owned}),
        allow_tokens=set(),
        deny_tokens=set(),
        apply_agent_narrowing=True,
        agent_store_ids=frozenset({owned, foreign}),
        universe_store_ids=frozenset({owned, foreign}),
    )

    assert narrowed == frozenset({owned})
    assert cannot_expand == frozenset({owned})


def test_missing_and_malformed_rules_fail_closed() -> None:
    with pytest.raises(APIError) as missing:
        resolve_store_scope(
            set(),
            role_rules=[],
            global_rules=[],
            owned_store_ids=frozenset(),
            allow_tokens=set(),
            deny_tokens=set(),
            apply_agent_narrowing=False,
            agent_store_ids=frozenset(),
            universe_store_ids=frozenset(),
        )
    with pytest.raises(APIError) as malformed:
        resolve_store_scope(
            {"all"},
            role_rules=[],
            global_rules=[("storeIds", ["not-a-uuid"])],
            owned_store_ids=frozenset(),
            allow_tokens=set(),
            deny_tokens=set(),
            apply_agent_narrowing=False,
            agent_store_ids=frozenset(),
            universe_store_ids=frozenset(),
        )

    assert missing.value.code.value == "VALIDATION_FAILED"
    assert malformed.value.code.value == "VALIDATION_FAILED"
