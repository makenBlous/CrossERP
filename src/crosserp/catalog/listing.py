"""平台 Listing 业务服务。"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.schemas import (
    ListingCreateRequest,
    ListingStatusRequest,
    ListingUpdateRequest,
)
from crosserp.db.schema import ActionExecution, Listing, Store
from crosserp.iam.scope import AllStores, StoreScope, apply_store_scope
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier
from crosserp.platform.factory import make_action_dispatcher
from crosserp.platform.idempotency import (
    caller_scope,
    current_http_scope,
    find_action_replay,
    scope_hash,
)
from crosserp.platform.permissions import PermissionService
from crosserp.platform.principal import Principal


class ListingService:
    def __init__(
        self,
        session: Session,
        principal: Principal,
        permission_service: PermissionService,
        *,
        request_id: str | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        self.session = session
        self.principal = principal
        self.permission_service = permission_service
        self.request_id = request_id
        self.tool_call_id = tool_call_id

    def list(self, *, page: int, page_size: int, q: str | None, sort: str | None) -> dict[str, Any]:
        self.permission_service.require(self.principal, "listing:read")
        statement = select(Listing)
        statement = self._scope_statement(statement)
        if q:
            statement = statement.where(Listing.platform_sku.contains(q) | Listing.asin.contains(q))
        sort_key = (sort or "-updatedAt").lstrip("-")
        descending = bool(sort and sort.startswith("-"))
        columns = {
            "id": Listing.id,
            "platformSku": Listing.platform_sku,
            "status": Listing.status,
            "updatedAt": Listing.updated_at,
            "createdAt": Listing.created_at,
        }
        if sort_key not in columns:
            raise APIError(ErrorCode.VALIDATION_ERROR, "sort 字段不支持")
        column = columns[sort_key]
        ordered = column.desc() if descending else column.asc()
        statement = statement.order_by(ordered, Listing.id.asc())
        total = int(
            self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        )
        rows = list(self.session.scalars(statement.offset((page - 1) * page_size).limit(page_size)))
        return {
            "items": [_listing_dict(row) for row in rows],
            "page": page,
            "pageSize": page_size,
            "total": total,
        }

    def get(self, listing_id: UUID) -> dict[str, Any]:
        self.permission_service.require(self.principal, "listing:read", listing_id)
        row = self._get_scoped(listing_id)
        return _listing_dict(row)

    def create(self, payload: ListingCreateRequest, idempotency_key: str | None) -> dict[str, Any]:
        self.permission_service.require(self.principal, "listing:create")
        store_id = payload.store_id
        store = self.session.get(Store, store_id)
        if store is None:
            raise not_found(message="店铺不存在")
        self._require_store_scope(store_id, write=True)
        platform_sku = payload.platform_sku
        price = Decimal(payload.price.amount_minor).scaleb(-4)
        currency = payload.price.currency
        now = datetime.now(UTC)
        listing = Listing(
            id=uuid4(),
            store_id=store_id,
            platform_sku=platform_sku,
            asin=payload.asin,
            price=price,
            currency=currency,
            status=payload.status,
            version=1,
            created_at=now,
            updated_at=now,
            provenance_json=_provenance(self.principal),
        )

        def business_action() -> dict[str, Any]:
            if (
                self.session.scalar(
                    select(Listing).where(
                        Listing.store_id == store_id, Listing.platform_sku == platform_sku
                    )
                )
                is not None
            ):
                raise APIError(ErrorCode.CONFLICT_VERSION, "Listing 已存在")
            self.session.add(listing)
            self.session.flush()
            result = _listing_dict(listing)
            result["before"] = {"storeId": str(store_id)}
            result["undoPayload"] = {"action": "Listing.update", "before": result["before"]}
            return result

        dispatcher = self._dispatcher()
        return cast(
            dict[str, Any],
            dispatcher.dispatch(
                principal=self.principal,
                permission="listing:create",
                risk_tier=RiskTier.MEDIUM,
                action="Listing.create",
                entity="Listing",
                entity_id=listing.id,
                payload=payload.model_dump(by_alias=True, mode="json"),
                idempotency_key=idempotency_key,
                request_id=self.request_id,
                tool_call_id=self.tool_call_id,
                business_action=business_action,
            ),
        )

    def update(
        self,
        listing_id: UUID,
        payload: ListingUpdateRequest,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self.permission_service.require(self.principal, "listing:write", listing_id)
        listing = self._get_scoped(listing_id, write=True)
        expected_version = payload.expected_version
        before = _listing_dict(listing)

        def business_action() -> dict[str, Any]:
            if "status" in payload.model_fields_set and payload.status is not None:
                listing.status = payload.status
            if "asin" in payload.model_fields_set:
                listing.asin = payload.asin
            if "price" in payload.model_fields_set and payload.price is not None:
                listing.price = Decimal(payload.price.amount_minor).scaleb(-4)
                listing.currency = payload.price.currency
            listing.version += 1
            listing.updated_at = datetime.now(UTC)
            listing.provenance_json = _provenance(self.principal)
            self.session.flush()
            result = _listing_dict(listing)
            result["before"] = before
            result["undoPayload"] = {"action": "Listing.update", "before": before}
            return result

        return cast(
            dict[str, Any],
            self._dispatcher().dispatch(
                principal=self.principal,
                permission="listing:write",
                risk_tier=RiskTier.MEDIUM,
                action="Listing.update",
                entity="Listing",
                entity_id=listing.id,
                payload=payload.model_dump(by_alias=True, mode="json"),
                expected_version=expected_version,
                idempotency_key=idempotency_key,
                request_id=self.request_id,
                tool_call_id=self.tool_call_id,
                business_action=business_action,
            ),
        )

    def status(
        self,
        payload: ListingStatusRequest,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self.permission_service.require(self.principal, "listing:write")
        target_status = payload.status
        batch_payload = payload.model_dump(by_alias=True, mode="json")
        for listing_id in payload.ids:
            self._get_scoped(listing_id, write=True)
        if idempotency_key:
            replay = find_action_replay(
                self.session,
                self.principal,
                key=idempotency_key,
                payload=batch_payload,
                action="Listing.status",
            )
            if replay is not None:
                return cast(dict[str, Any], replay)
        items: list[dict[str, Any]] = []
        for index, listing_id in enumerate(payload.ids):
            listing = self._get_scoped(listing_id, write=True)
            before = _listing_dict(listing)

            def business_action(
                listing: Listing = listing,
                before: dict[str, Any] = before,
                target_status: str = target_status,
            ) -> dict[str, Any]:
                listing.status = target_status
                listing.version += 1
                listing.updated_at = datetime.now(UTC)
                listing.provenance_json = _provenance(self.principal)
                self.session.flush()
                result = _listing_dict(listing)
                result["before"] = before
                result["undoPayload"] = {"action": "Listing.update", "before": before}
                return result

            item_key = idempotency_key if index == 0 else None
            item_expected = payload.expected_version
            item = cast(
                dict[str, Any],
                self._dispatcher().dispatch(
                    principal=self.principal,
                    permission="listing:write",
                    risk_tier=RiskTier.MEDIUM,
                    action="Listing.status",
                    entity="Listing",
                    entity_id=listing.id,
                    payload=batch_payload,
                    expected_version=item_expected,
                    idempotency_key=item_key,
                    request_id=self.request_id,
                    tool_call_id=self.tool_call_id,
                    business_action=business_action,
                ),
            )
            items.append(item)
        result = {"updated": len(items), "items": items}
        if idempotency_key:
            identity = caller_scope(self.principal)
            http = current_http_scope("Listing.status")
            execution = self.session.scalar(
                select(ActionExecution).where(
                    ActionExecution.idempotency_scope_hash
                    == scope_hash(
                        caller_identity=identity.caller_identity,
                        method=http.method,
                        route_template=http.route_template,
                        key=idempotency_key,
                    )
                )
            )
            if execution is not None:
                execution.result_json = result
                self.session.flush()
        return result

    def _dispatcher(self) -> ActionDispatcher:
        return make_action_dispatcher(self.session, self.permission_service)

    def _store_scope(self) -> StoreScope:
        return self.permission_service.store_scope(self.principal, "Listing")

    def _scope_statement(self, statement: Any) -> Any:
        return apply_store_scope(statement, Listing.store_id, self._store_scope())

    def _get_scoped(self, listing_id: UUID, *, write: bool = False) -> Listing:
        statement = select(Listing).where(Listing.id == listing_id)
        if write:
            statement = statement.with_for_update()
        row = self.session.scalar(self._scope_statement(statement))
        if row is None:
            if write:
                existing = self.session.get(Listing, listing_id)
                if existing is not None:
                    raise APIError(ErrorCode.DATA_SCOPE_DENIED, "超出店铺数据范围")
            raise not_found(message="Listing 不存在")
        return cast(Listing, row)

    def _require_store_scope(self, store_id: UUID, *, write: bool) -> None:
        scope = self._store_scope()
        if isinstance(scope, AllStores) or store_id in scope:
            return
        if write:
            raise APIError(ErrorCode.DATA_SCOPE_DENIED, "超出店铺数据范围")
        raise not_found(message="Listing 不存在")


def _provenance(principal: Principal) -> dict[str, Any]:
    return {
        "actorType": "agent" if principal.is_agent else "human",
        "actorId": str(principal.user_id) if principal.user_id else None,
        "onBehalfOf": str(principal.on_behalf_of) if principal.on_behalf_of else None,
    }


def _listing_dict(row: Listing) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "storeId": str(row.store_id),
        "platformSku": row.platform_sku,
        "asin": row.asin,
        "price": {"amountMinor": int(row.price * 10000), "currency": row.currency},
        "status": row.status,
        "version": row.version,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
        "provenance": row.provenance_json,
    }


__all__ = ["ListingService"]
