"""平台 Listing 业务服务。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.schemas import Money
from crosserp.db.schema import ActionExecution, Listing, Store
from crosserp.platform.dispatcher import ActionDispatcher, RiskTier, _request_hash
from crosserp.platform.permissions import DefaultPermissionService, PermissionService
from crosserp.platform.principal import Principal


class ListingService:
    def __init__(
        self,
        session: Session,
        principal: Principal,
        permission_service: PermissionService | None = None,
        *,
        request_id: str | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        self.session = session
        self.principal = principal
        self.permission_service = permission_service or DefaultPermissionService()
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
            raise APIError(ErrorCode.VALIDATION_FAILED, "sort 字段不支持")
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

    def create(self, payload: Mapping[str, Any], idempotency_key: str | None) -> dict[str, Any]:
        self.permission_service.require(self.principal, "listing:create")
        store_id = _uuid(payload.get("storeId"), "storeId")
        store = self.session.get(Store, store_id)
        if store is None:
            raise not_found(message="店铺不存在")
        self._require_store_scope(store_id, write=True)
        platform_sku = _required_text(payload, "platformSku", 128)
        price, currency = _money(payload.get("price"))
        now = datetime.now(UTC)
        listing = Listing(
            id=uuid4(),
            store_id=store_id,
            platform_sku=platform_sku,
            asin=_optional_text(payload.get("asin"), "asin", 64),
            price=price,
            currency=currency,
            status=_status(payload.get("status", "active")),
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
            result["undoPayload"] = {"action": "Listing.update", "before": None}
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
                payload=dict(payload),
                idempotency_key=idempotency_key,
                request_id=self.request_id,
                tool_call_id=self.tool_call_id,
                business_action=business_action,
            ),
        )

    def update(
        self,
        listing_id: UUID,
        payload: Mapping[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        self.permission_service.require(self.principal, "listing:write", listing_id)
        listing = self._get_scoped(listing_id, write=True)
        expected_version = _expected_version(payload, required=True)
        before = _listing_dict(listing)

        def business_action() -> dict[str, Any]:
            if "status" in payload:
                listing.status = _status(payload["status"])
            if "asin" in payload:
                listing.asin = _optional_text(payload["asin"], "asin", 64)
            if "price" in payload:
                listing.price, listing.currency = _money(payload["price"])
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
                payload=dict(payload),
                expected_version=expected_version,
                idempotency_key=idempotency_key,
                request_id=self.request_id,
                tool_call_id=self.tool_call_id,
                business_action=business_action,
            ),
        )

    def status(
        self,
        listing_ids: Sequence[UUID],
        status: Any,
        expected_version: int | Mapping[str, Any],
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self.permission_service.require(self.principal, "listing:write")
        target_status = _status(status)
        batch_payload = {
            "ids": [str(listing_id) for listing_id in listing_ids],
            "status": target_status,
            "expectedVersion": expected_version,
        }
        if idempotency_key:
            replay = self.session.scalar(
                select(ActionExecution).where(ActionExecution.idempotency_key == idempotency_key)
            )
            if replay is not None:
                if replay.request_hash != _request_hash(batch_payload):
                    raise APIError(ErrorCode.IDEMPOTENCY_REPLAY_MISMATCH, "幂等键对应了不同请求体")
                return cast(dict[str, Any], replay.result_json)
        items: list[dict[str, Any]] = []
        for index, listing_id in enumerate(listing_ids):
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
                result["undoPayload"] = {"action": "Listing.update", "before": before}
                return result

            item_key = idempotency_key if index == 0 else None
            item_expected = (
                expected_version
                if isinstance(expected_version, int)
                else expected_version.get(str(listing_id))
            )
            if (
                not isinstance(item_expected, int)
                or isinstance(item_expected, bool)
                or item_expected < 1
            ):
                raise APIError(ErrorCode.VALIDATION_FAILED, "expectedVersion 必须覆盖每个 Listing")
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
            execution = self.session.scalar(
                select(ActionExecution).where(ActionExecution.idempotency_key == idempotency_key)
            )
            if execution is not None:
                execution.result_json = result
                self.session.flush()
        return result

    def _dispatcher(self) -> ActionDispatcher:
        return ActionDispatcher(session=self.session, permission_service=self.permission_service)

    def _scope_statement(self, statement: Any) -> Any:
        ids = _scope_store_ids(self.permission_service.data_scope_filter(self.principal, "Listing"))
        if ids is not None:
            statement = statement.where(Listing.store_id.in_(ids))
        return statement

    def _get_scoped(self, listing_id: UUID, *, write: bool = False) -> Listing:
        statement = select(Listing).where(Listing.id == listing_id)
        if write:
            statement = statement.with_for_update()
        row = self.session.scalar(self._scope_statement(statement))
        if row is None:
            if write:
                existing = self.session.get(Listing, listing_id)
                if existing is not None:
                    raise APIError(ErrorCode.DATA_SCOPE_DENIED, "超出店铺数据范围", status_code=403)
            raise not_found(message="Listing 不存在")
        return cast(Listing, row)

    def _require_store_scope(self, store_id: UUID, *, write: bool) -> None:
        ids = _scope_store_ids(self.permission_service.data_scope_filter(self.principal, "Listing"))
        if ids is not None and store_id not in ids:
            if write:
                raise APIError(ErrorCode.DATA_SCOPE_DENIED, "超出店铺数据范围", status_code=403)
            raise not_found(message="Listing 不存在")


def _scope_store_ids(scope: Mapping[str, Any]) -> set[UUID] | None:
    values: Any = scope.get("store_ids", scope.get("storeIds"))
    if values is None:
        return None
    if isinstance(values, str):
        return {UUID(values)}
    return {value if isinstance(value, UUID) else UUID(str(value)) for value in values}


def _uuid(value: Any, field: str) -> UUID:
    if isinstance(value, UUID):
        return value
    if not isinstance(value, str):
        raise APIError(ErrorCode.VALIDATION_FAILED, f"{field} 必须是 UUID")
    try:
        return UUID(value)
    except ValueError as exc:
        raise APIError(ErrorCode.VALIDATION_FAILED, f"{field} 必须是 UUID") from exc


def _required_text(payload: Mapping[str, Any], field: str, limit: int) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value or len(value) > limit:
        raise APIError(ErrorCode.VALIDATION_FAILED, f"{field} 必须是 1-{limit} 个字符")
    return value


def _optional_text(value: Any, field: str, limit: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > limit:
        raise APIError(ErrorCode.VALIDATION_FAILED, f"{field} 长度超限")
    return value


def _money(value: Any) -> tuple[Decimal, str]:
    try:
        parsed = Money.model_validate(value)
    except ValueError as exc:
        raise APIError(ErrorCode.VALIDATION_FAILED, "price 必须是 Money") from exc
    return Decimal(parsed.amount_minor).scaleb(-4), parsed.currency


def _status(value: Any) -> str:
    if value == "active" or value == "inactive":
        return cast(str, value)
    raise APIError(ErrorCode.ILLEGAL_TRANSITION, "Listing 状态只能是 active 或 inactive")


def _expected_version(payload: Mapping[str, Any], *, required: bool = False) -> int | None:
    value = payload.get("expectedVersion")
    if value is None:
        if required:
            raise APIError(ErrorCode.VALIDATION_FAILED, "expectedVersion 必须提供")
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise APIError(ErrorCode.VALIDATION_FAILED, "expectedVersion 必须是正整数")
    return value


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
