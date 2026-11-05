"""FastAPI 网页应用、登录会话和只读报表页。"""

from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp import __version__
from crosserp.audit.security import SecurityEventName
from crosserp.audit.security import record as record_security
from crosserp.auth.passwords import hash_password, verify_password
from crosserp.auth.permissions import Permission
from crosserp.auth.sessions import create_session, find_user, revoke_session
from crosserp.config import load_settings
from crosserp.db.migrate import ensure_database_directory, upgrade_head
from crosserp.db.repo.users import get_by_username
from crosserp.db.schema import (
    AppSetting,
    AppUser,
    ImportBatch,
    Issue,
    ProfitSnapshot,
    SecurityEvent,
    Store,
)
from crosserp.db.session import get_database_url, make_engine, session_scope
from crosserp.issues.catalog import definition, render
from crosserp.web.deps import require

_WEB_DIR = Path(__file__).parent
_DUMMY_HASH = hash_password("CrossERP dummy password value")


def create_app(database_url: str | None = None) -> FastAPI:
    """创建应用。健康检查和静态资源匿名, 其余页面需要登录。"""
    app = FastAPI()
    templates = Jinja2Templates(directory=_WEB_DIR / "templates")
    settings = load_settings()
    app.mount("/static", StaticFiles(directory=_WEB_DIR / "static"), name="static")
    resolved = database_url or get_database_url()
    ensure_database_directory(resolved)
    upgrade_head(resolved)
    engine = make_engine(resolved)

    @contextmanager
    def sessions() -> Iterator[Session]:
        with session_scope(engine) as session:
            yield session

    def current(request: Request, session: Session) -> AppUser | None:
        return find_user(session, request.cookies.get("crosserp_session"))

    def login_redirect(request: Request) -> Response:
        if request.headers.get("HX-Request") or "application/json" in request.headers.get(
            "Accept", ""
        ):
            return Response(status_code=401)
        return RedirectResponse(f"/login?next={_safe_next(request.url.path)}", status_code=302)

    def permission_denied(
        session: Session, user: AppUser, request: Request, permission: str
    ) -> Response:
        record_security(
            session,
            SecurityEventName.PERMISSION_DENIED,
            user_id=user.id,
            username=user.username,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            detail={"permission": permission, "path": request.url.path, "method": request.method},
        )
        return Response("你没有权限做这件事", status_code=403)

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, next: str = "/") -> Response:
        response = templates.TemplateResponse(
            request, "login.html", {"next": _safe_next(next), "error": None}
        )
        response.set_cookie(
            "crosserp_login_csrf", secrets.token_urlsafe(24), samesite="lax", path="/"
        )
        return response

    @app.post("/login", response_class=HTMLResponse)
    def login(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        next: str = Form("/"),
        csrf_token: str = Form(""),
    ) -> Response:
        if not csrf_token or csrf_token != request.cookies.get("crosserp_login_csrf"):
            return Response("CSRF 校验失败", status_code=403)
        now = datetime.now(UTC)
        with sessions() as session:
            user = get_by_username(session, username)
            valid = verify_password(user.password_hash if user else _DUMMY_HASH, password)
            locked = user is not None and user.locked_until is not None and user.locked_until > now
            if user is None or not user.is_active or locked or not valid:
                if user is not None and not locked:
                    user.failed_logins += 1
                    if user.failed_logins >= settings.auth.max_failed_logins:
                        user.locked_until = now + timedelta(minutes=settings.auth.lockout_minutes)
                message = "账号已锁定，请稍后再试。" if locked else "账号或密码错误。"  # noqa: RUF001
                record_security(
                    session,
                    SecurityEventName.LOGIN_FAILED,
                    user_id=user.id if user else None,
                    username=username,
                    ip=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                return templates.TemplateResponse(
                    request,
                    "login.html",
                    {"next": _safe_next(next), "error": message},
                    status_code=401,
                )
            user.failed_logins = 0
            user.locked_until = None
            record_security(
                session,
                SecurityEventName.LOGIN_SUCCESS,
                user_id=user.id,
                username=user.username,
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            token = create_session(
                session,
                user,
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                hours=settings.auth.session_hours,
            )
        response = RedirectResponse(_safe_next(next), status_code=303)
        secure = settings.cookie_secure or request.url.scheme == "https"
        response.set_cookie(
            "crosserp_session", token.value, httponly=True, samesite="lax", path="/", secure=secure
        )
        response.set_cookie(
            "crosserp_csrf",
            token.csrf_token,
            httponly=False,
            samesite="lax",
            path="/",
            secure=secure,
        )
        return response

    @app.post("/logout")
    def logout(request: Request, csrf_token: str = Form(...)) -> Response:
        if request.cookies.get("crosserp_csrf") != csrf_token:
            return Response("CSRF 校验失败", status_code=403)
        with sessions() as session:
            revoke_session(session, request.cookies.get("crosserp_session"))
            record_security(
                session,
                SecurityEventName.LOGOUT,
                username=None,
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie("crosserp_session", path="/")
        response.delete_cookie("crosserp_csrf", path="/")
        return response

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> Response:
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.REPORT_READ):
                return permission_denied(session, user, request, Permission.REPORT_READ.value)
            stores = list(session.scalars(select(Store).order_by(Store.name)))
        return templates.TemplateResponse(
            request, "index.html", {"version": __version__, "stores": stores, "user": user}
        )

    @app.get("/imports", response_class=HTMLResponse)
    def imports_page(request: Request) -> Response:
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.REPORT_READ):
                return permission_denied(session, user, request, Permission.REPORT_READ.value)
            batches = list(
                session.scalars(
                    select(ImportBatch).order_by(ImportBatch.imported_at.desc()).limit(100)
                )
            )
        return templates.TemplateResponse(
            request, "imports.html", {"request": request, "batches": batches, "user": user}
        )

    @app.get("/profit", response_class=HTMLResponse)
    def profit_page(
        request: Request, store: str | None = None, period: str | None = None
    ) -> Response:
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.REPORT_READ):
                return permission_denied(session, user, request, Permission.REPORT_READ.value)
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
            {"request": request, "rows": rows, "period": period, "store": store, "user": user},
        )

    @app.get("/issues", response_class=HTMLResponse)
    def issues_page(
        request: Request,
        kind: str | None = None,
        severity: str | None = None,
        page: int = Query(1, ge=1),
    ) -> Response:
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.REPORT_READ):
                return permission_denied(session, user, request, Permission.REPORT_READ.value)
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
            {
                "request": request,
                "rows": rows,
                "kind": kind,
                "severity": severity,
                "page": page,
                "user": user,
            },
        )

    @app.get("/security-log", response_class=HTMLResponse)
    def security_log(request: Request) -> Response:
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.SECURITY_LOG_READ):
                return permission_denied(session, user, request, Permission.SECURITY_LOG_READ.value)
            rows = list(
                session.scalars(select(SecurityEvent).order_by(SecurityEvent.seq.desc()).limit(100))
            )
        return templates.TemplateResponse(
            request, "security_log.html", {"request": request, "rows": rows, "user": user}
        )

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request) -> Response:
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.SETTING_MANAGE):
                return permission_denied(session, user, request, Permission.REPORT_READ.value)
            setting = session.get(AppSetting, "solo_mode")
            enabled = bool(setting.value_json) if setting is not None else False
        state = "开" if enabled else "关"
        csrf = request.cookies.get("crosserp_csrf", "")
        solo_value = str(not enabled).lower()
        body = (
            f"<h1>系统设置</h1><p>单人模式：{state}</p>"  # noqa: RUF001
            f"<form method='post'><input type='hidden' name='solo_mode' value='{solo_value}'>"
            f"<input type='hidden' name='csrf_token' value='{csrf}'><button>切换</button></form>"
        )
        return HTMLResponse(body)

    @app.post("/settings")
    def settings_update(
        request: Request, solo_mode: str = Form(...), csrf_token: str = Form(...)
    ) -> Response:
        if csrf_token != request.cookies.get("crosserp_csrf"):
            return Response("CSRF 校验失败", status_code=403)
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.SETTING_MANAGE):
                return permission_denied(session, user, request, Permission.REPORT_READ.value)
            setting = session.get(AppSetting, "solo_mode")
            if setting is None:
                session.add(
                    AppSetting(
                        key="solo_mode",
                        value_json=solo_mode == "true",
                        updated_by=user.id,
                        updated_at=datetime.now(UTC),
                    )
                )
            else:
                setting.value_json = solo_mode == "true"
                setting.updated_by = user.id
                setting.updated_at = datetime.now(UTC)
        return RedirectResponse("/settings", status_code=303)

    return app


def _safe_next(value: str) -> str:
    parsed = urlparse(value or "/")
    if parsed.scheme or parsed.netloc or not value.startswith("/") or value.startswith("//"):
        return "/"
    return value
