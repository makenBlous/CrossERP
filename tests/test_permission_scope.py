from uuid import uuid4

from crosserp.platform.permissions import DefaultPermissionService, entity_matches_scope
from crosserp.platform.principal import Principal


class _ScopeIam:
    def __init__(self, scope: dict[str, object]) -> None:
        self.scope = scope

    def data_scope_filter(self, _principal: Principal, _entity: str) -> dict[str, object]:
        return self.scope


def test_entity_in_scope_honors_all_id_filter_and_store_filter() -> None:
    service = DefaultPermissionService(_ScopeIam({"scopes": ["all"], "filters": {"storeIds": []}}))
    principal = Principal(user_id=uuid4())
    sku_id = str(uuid4())
    assert service.entity_in_scope(principal, "Sku", sku_id, {"storeId": str(uuid4())})

    limited = DefaultPermissionService(
        _ScopeIam({"scopes": ["store"], "filters": {"skuIds": [sku_id], "storeIds": ["store-1"]}})
    )
    assert limited.entity_in_scope(principal, "Sku", sku_id, {"storeId": "store-1"})
    assert not limited.entity_in_scope(principal, "Sku", str(uuid4()), {"storeId": "store-1"})
    assert not limited.entity_in_scope(principal, "Sku", sku_id, {"storeId": "store-2"})
    assert not limited.entity_in_scope(principal, "Sku", sku_id, None)
    assert entity_matches_scope(
        {"scopes": ["store"], "filters": {"storeIds": ["store-1"]}},
        "Supplier",
        str(uuid4()),
        {},
    )
