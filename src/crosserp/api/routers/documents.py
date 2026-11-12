# ruff: noqa: B008
"""DocumentLink 查询接口。"""

from __future__ import annotations

from collections import deque
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field
from sqlalchemy import select

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _page, _principal_db, _require
from crosserp.api.schemas import PageParams
from crosserp.db.schema import DocumentLink
from crosserp.iam.scope import AllStores, StoreScope

router = APIRouter()


class DocumentPageParams(PageParams):
    """DocumentLink 分页契约的默认 pageSize 为 20。"""

    page_size: int = Field(default=20, alias="pageSize", ge=1, le=200)


def _link_payload(row: DocumentLink) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "from": {"type": row.from_type, "id": row.from_id},
        "to": {"type": row.to_type, "id": row.to_id},
        "relation": row.relation,
    }


def _scope_nodes(rows: list[DocumentLink], scope: StoreScope) -> set[tuple[str, str]]:
    if isinstance(scope, AllStores):
        return {
            (kind, identifier)
            for row in rows
            for kind, identifier in ((row.from_type, row.from_id), (row.to_type, row.to_id))
        }

    allowed_stores = {str(store_id) for store_id in scope}
    adjacency: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for row in rows:
        source = (row.from_type, row.from_id)
        target = (row.to_type, row.to_id)
        if (source[0] == "Store" and source[1] not in allowed_stores) or (
            target[0] == "Store" and target[1] not in allowed_stores
        ):
            continue
        adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set()).add(source)

    visible: set[tuple[str, str]] = {("Store", store_id) for store_id in allowed_stores}
    queue = deque(visible)
    while queue:
        node = queue.popleft()
        for neighbor in adjacency.get(node, ()):
            if neighbor not in visible:
                visible.add(neighbor)
                queue.append(neighbor)
    return visible


def _visible_rows(rows: list[DocumentLink], scope: StoreScope) -> list[DocumentLink]:
    visible_nodes = _scope_nodes(rows, scope)
    return [
        row
        for row in rows
        if (row.from_type, row.from_id) in visible_nodes
        and (row.to_type, row.to_id) in visible_nodes
    ]


@router.get("/documents/links")
@api_endpoint(
    entity="DocumentLink",
    action="DocumentLink.read_links",
    permission="document:read",
    risk_tier="none",
    idempotency="none",
)
def links(
    request: Request,
    params: DocumentPageParams = Depends(),
    q: str | None = Query(default=None),
    sort: str = Query(default="-createdAt"),
) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _require(request, principal, "document:read", entity="DocumentLink")
        if sort not in {"createdAt", "-createdAt"}:
            raise APIError(ErrorCode.VALIDATION_FAILED, "sort 参数无效")
        ordering = (
            DocumentLink.created_at.asc() if sort == "createdAt" else DocumentLink.created_at.desc()
        )
        rows = list(
            session.scalars(select(DocumentLink).order_by(ordering, DocumentLink.id.desc()))
        )
        scope = request.app.state.permission_service.store_scope(principal, "DocumentLink")
        visible_rows = _visible_rows(rows, scope)
        if q:
            visible_rows = [
                row
                for row in visible_rows
                if q in row.from_type
                or q in row.from_id
                or q in row.to_type
                or q in row.to_id
                or q in row.relation
            ]
        start = (params.page - 1) * params.page_size
        page_rows = visible_rows[start : start + params.page_size]
        return _page(params, [_link_payload(row) for row in page_rows], len(visible_rows))
    finally:
        session.close()


@router.get("/documents/chain/{docType}/{id}")
@api_endpoint(
    entity="DocumentLink",
    action="DocumentLink.read_chain",
    permission="report:read",
    risk_tier="none",
    idempotency="none",
)
def chain(request: Request, docType: str, id: str) -> dict[str, Any]:
    principal, session = _principal_db(request)
    try:
        _require(request, principal, "report:read", entity="DocumentLink")
        rows = list(
            session.scalars(
                select(DocumentLink).order_by(
                    DocumentLink.created_at.desc(), DocumentLink.id.desc()
                )
            )
        )
        scope = request.app.state.permission_service.store_scope(principal, "DocumentLink")
        visible_rows = _visible_rows(rows, scope)
        root = (docType, id)
        if not any(
            root in ((row.from_type, row.from_id), (row.to_type, row.to_id)) for row in visible_rows
        ):
            raise not_found()

        adjacency: dict[tuple[str, str], list[DocumentLink]] = {}
        for row in visible_rows:
            adjacency.setdefault((row.from_type, row.from_id), []).append(row)
            adjacency.setdefault((row.to_type, row.to_id), []).append(row)

        visited_nodes = {root}
        visited_links: set[str] = set()
        queue = deque([root])
        while queue:
            node = queue.popleft()
            for row in adjacency[node]:
                visited_links.add(str(row.id))
                other = (
                    (row.to_type, row.to_id)
                    if node == (row.from_type, row.from_id)
                    else (row.from_type, row.from_id)
                )
                if other not in visited_nodes:
                    visited_nodes.add(other)
                    queue.append(other)

        links_payload = [
            {
                "id": str(row.id),
                "fromType": row.from_type,
                "fromId": row.from_id,
                "toType": row.to_type,
                "toId": row.to_id,
                "relation": row.relation,
            }
            for row in visible_rows
            if str(row.id) in visited_links
        ]
        return {"entity": {"type": docType, "id": id}, "links": links_payload}
    finally:
        session.close()


__all__ = ["router"]
