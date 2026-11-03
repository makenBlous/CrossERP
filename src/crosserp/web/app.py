"""FastAPI read-only web pages."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp import __version__
from crosserp.db.schema import ImportBatch, Issue, ProfitSnapshot, Store
from crosserp.db.session import get_database_url, make_engine, session_scope
from crosserp.issues.catalog import definition, render

_WEB_DIR = Path(__file__).parent


def create_app(database_url: str | None = None) -> FastAPI:
    """Create a read-only application. Every business route is GET-only."""
    app = FastAPI()
    templates = Jinja2Templates(directory=_WEB_DIR / "templates")
    app.mount("/static", StaticFiles(directory=_WEB_DIR / "static"), name="static")
    engine = make_engine(database_url or get_database_url())

    @contextmanager
    def sessions() -> Iterator[Session]:
        with session_scope(engine) as session:
            yield session

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> Response:
        with sessions() as session:
            stores = list(session.scalars(select(Store).order_by(Store.name)))
        return templates.TemplateResponse(
            request, "index.html", {"version": __version__, "stores": stores}
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/imports", response_class=HTMLResponse)
    def imports_page(request: Request) -> Response:
        with sessions() as session:
            batches = list(
                session.scalars(
                    select(ImportBatch).order_by(ImportBatch.imported_at.desc()).limit(100)
                )
            )
        return templates.TemplateResponse(
            request, "imports.html", {"request": request, "batches": batches}
        )

    @app.get("/profit", response_class=HTMLResponse)
    def profit_page(
        request: Request, store: str | None = None, period: str | None = None
    ) -> Response:
        with sessions() as session:
            statement = select(ProfitSnapshot, Store).join(
                Store, Store.id == ProfitSnapshot.store_id
            )
            if store:
                statement = statement.where(Store.name == store)
            if period:
                statement = statement.where(ProfitSnapshot.period == period)
            rows = list(
                session.execute(statement.order_by(Store.name, ProfitSnapshot.internal_sku))
            )
        return templates.TemplateResponse(
            request,
            "profit.html",
            {"request": request, "rows": rows, "period": period, "store": store},
        )

    @app.get("/issues", response_class=HTMLResponse)
    def issues_page(
        request: Request,
        kind: str | None = None,
        severity: str | None = None,
        page: int = Query(1, ge=1),
    ) -> Response:
        with sessions() as session:
            statement = select(Issue).order_by(Issue.created_at.desc())
            if kind:
                statement = statement.where(Issue.kind == kind)
            if severity:
                statement = statement.where(Issue.severity == severity)
            issues = list(session.scalars(statement.offset((page - 1) * 50).limit(50)))
            rows = [(issue, definition(issue.kind), render(issue)) for issue in issues]
        return templates.TemplateResponse(
            request,
            "issues.html",
            {"request": request, "rows": rows, "kind": kind, "severity": severity, "page": page},
        )

    return app
