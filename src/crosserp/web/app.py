"""FastAPI 网页应用、登录会话和只读报表页。"""

from __future__ import annotations

import hashlib
import os
import tempfile
import time
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from crosserp import __version__
from crosserp.agent.runtime import ask as ask_agent
from crosserp.api import install_api
from crosserp.approval.service import approve as approve_approval
from crosserp.approval.service import check_fresh
from crosserp.approval.service import create as create_approval
from crosserp.approval.service import reject as reject_approval
from crosserp.approval.service import submit as submit_approval
from crosserp.approval.state import ConcurrentModification
from crosserp.audit.diff import diff_json
from crosserp.audit.export import export_audit
from crosserp.audit.log import append, verify_chain
from crosserp.audit.security import SecurityEventName
from crosserp.audit.security import record as record_security
from crosserp.auth.passwords import hash_password, verify_password
from crosserp.auth.permissions import Permission
from crosserp.auth.sessions import create_session, find_user, revoke_session
from crosserp.auth.tokens import create_token
from crosserp.config import load_settings
from crosserp.db.migrate import ensure_database_directory, upgrade_head
from crosserp.db.repo.users import create_user, get_by_username, grant_role, list_users
from crosserp.db.schema import (
    Approval,
    AppSetting,
    AppUser,
    AuditHead,
    AuditLog,
    ExportArtifact,
    ImportBatch,
    Issue,
    LlmCall,
    OrderLine,
    ProfitSnapshot,
    RawRow,
    SecurityEvent,
    SettlementLine,
    Store,
    Voucher,
    VoucherLine,
)
from crosserp.db.session import get_database_url, make_engine, session_scope
from crosserp.issues.catalog import definition, render
from crosserp.issues.service import transition as transition_issue
from crosserp.ledger.write_service import ApprovalRequired
from crosserp.ledger.write_service import export_many as export_ledger_many
from crosserp.observability.stats import summarize
from crosserp.web.csrf import login_form_token, valid_pair
from crosserp.web.deps import require

_WEB_DIR = Path(__file__).parent
_DUMMY_HASH = hash_password("CrossERP dummy password value")


def plain_text(content: str, status_code: int) -> PlainTextResponse:
    """纯文本必须声明 UTF-8. 响应带 nosniff, 未声明字符集时中文 Windows 会按 GBK 显示."""
    return PlainTextResponse(content, status_code=status_code)


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
    install_api(app, engine)
    ask_times: dict[str, list[float]] = {}

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
        return plain_text("你没有权限做这件事", 403)

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
        token, issue = login_form_token(request.cookies.get("crosserp_login_csrf"))
        response = templates.TemplateResponse(
            request,
            "login.html",
            {"next": _safe_next(next), "error": None, "csrf_token": token},
        )
        if issue:
            response.set_cookie("crosserp_login_csrf", token, samesite="lax", path="/")
        return response

    @app.post("/login", response_class=HTMLResponse)
    def login(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        next: str = Form("/"),
        csrf_token: str = Form(""),
    ) -> Response:
        if not valid_pair(request.cookies.get("crosserp_login_csrf"), csrf_token):
            return plain_text("CSRF 校验失败", 403)
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
                    {"next": _safe_next(next), "error": message, "csrf_token": csrf_token},
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
            return plain_text("CSRF 校验失败", 403)
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

    @app.post("/profit/submit")
    def profit_submit(
        request: Request,
        store: str = Form(...),
        period: str = Form(...),
        csrf_token: str = Form(...),
    ) -> Response:
        """从利润表提交一个利润报表审批单。"""
        if csrf_token != request.cookies.get("crosserp_csrf"):
            return plain_text("CSRF 校验失败", 403)
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.APPROVAL_SUBMIT):
                return permission_denied(session, user, request, Permission.APPROVAL_SUBMIT.value)
            target_id = f"{store}:{period}"
            try:
                row = create_approval(
                    session,
                    target_type="profit_report",
                    target_id=target_id,
                    requested_by=user.username,
                    payload_hash=_profit_report_payload_hash(session, target_id),
                    actor_role="operator",
                    actor_name=user.username,
                )
                submit_approval(
                    session,
                    row,
                    actor=user.username,
                    actor_role="operator",
                    actor_name=user.username,
                )
            except (LookupError, ValueError) as exc:
                return plain_text(str(exc), 400)
        return RedirectResponse("/profit", status_code=303)

    @app.get("/approvals", response_class=HTMLResponse)
    def approvals_page(request: Request, state: str = "pending") -> Response:
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.REPORT_READ):
                return permission_denied(session, user, request, Permission.REPORT_READ.value)
            allowed = {"pending", "approved", "rejected", "exported"}
            selected = state if state in allowed else "pending"
            rows = list(
                session.scalars(
                    select(Approval)
                    .where(Approval.state == selected)
                    .order_by(Approval.requested_at.desc(), Approval.id)
                )
            )
            can_decide = require(session, user, Permission.APPROVAL_DECIDE)
        return templates.TemplateResponse(
            request,
            "approvals.html",
            {
                "request": request,
                "rows": rows,
                "state": selected,
                "can_decide": can_decide,
                "user": user,
            },
        )

    @app.get("/approvals/{approval_id}", response_class=HTMLResponse)
    def approval_detail(request: Request, approval_id: str) -> Response:
        from uuid import UUID

        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.REPORT_READ):
                return permission_denied(session, user, request, Permission.REPORT_READ.value)
            try:
                row = session.get(Approval, UUID(approval_id))
            except ValueError:
                row = None
            if row is None:
                return plain_text("审批单不存在", 404)
            current_hash: str | None = None
            snapshots: list[tuple[ProfitSnapshot, Store]] = []
            if row.target_type == "profit_report":
                try:
                    current_hash = _profit_report_payload_hash(session, row.target_id)
                except (LookupError, ValueError):
                    current_hash = None
                if current_hash is not None and row.state == "approved":
                    check_fresh(
                        session,
                        row,
                        current_hash,
                        actor="system",
                        actor_name="web",
                    )
                store_name, _, period = row.target_id.rpartition(":")
                statement = select(ProfitSnapshot, Store).join(
                    Store, Store.id == ProfitSnapshot.store_id
                )
                statement = statement.where(ProfitSnapshot.period == period)
                statement = statement.where(
                    or_(Store.name == store_name, Store.id == _try_uuid(store_name))
                )
                snapshots = list(session.execute(statement.order_by(ProfitSnapshot.internal_sku)))
            fresh = current_hash is None or row.payload_hash == current_hash
            can_decide = require(session, user, Permission.APPROVAL_DECIDE)
        return templates.TemplateResponse(
            request,
            "approval_detail.html",
            {
                "request": request,
                "row": row,
                "snapshots": snapshots,
                "fresh": fresh,
                "can_decide": can_decide,
                "user": user,
            },
        )

    @app.post("/approvals/{approval_id}/decide")
    def approval_decide(
        request: Request,
        approval_id: str,
        action: str = Form(...),
        comment: str = Form(""),
        csrf_token: str = Form(...),
    ) -> Response:
        from uuid import UUID

        if csrf_token != request.cookies.get("crosserp_csrf"):
            return plain_text("CSRF 校验失败", 403)
        if action not in {"approve", "reject"}:
            return plain_text("不认识的审批动作", 400)
        if not comment.strip() or len(comment) > 1000:
            return plain_text("审批意见必填，且不能超过 1000 个字符", 400)  # noqa: RUF001
        approved_token: str | None = None
        approved_batch: str | None = None
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.APPROVAL_DECIDE):
                return permission_denied(session, user, request, Permission.APPROVAL_DECIDE.value)
            row = session.get(Approval, UUID(approval_id))
            if row is None:
                return plain_text("审批单不存在", 404)
            setting = session.get(AppSetting, "solo_mode")
            solo_mode = bool(setting.value_json) if setting is not None else False
            try:
                current_hash: str | None
                if row.target_type == "profit_report":
                    current_hash = _profit_report_payload_hash(session, row.target_id)
                else:
                    current_hash = row.payload_hash
                if action == "approve" and row.payload_hash != current_hash:
                    return plain_text("数据已变，需要重新提交", 400)  # noqa: RUF001
                if action == "approve":
                    approved_token = approve_approval(
                        session,
                        row,
                        approver=user.username,
                        payload_hash=current_hash,
                        actor_role="finance",
                        actor_name=user.username,
                        approver_user_id=user.id,
                        solo_mode=solo_mode,
                        comment=comment,
                    )
                    if row.target_type == "voucher":
                        approved_batch = f"{row.target_type}:{row.target_id}"
                else:
                    reject_approval(
                        session,
                        row,
                        approver=user.username,
                        comment=comment,
                        actor_role="finance",
                        actor_name=user.username,
                        approver_user_id=user.id,
                        solo_mode=solo_mode,
                    )
            except ConcurrentModification:
                return plain_text("别人刚处理过，请刷新", 409)  # noqa: RUF001
            except (LookupError, ValueError) as exc:
                return plain_text(str(exc), 400)
        if approved_token is not None and approved_batch is not None:
            try:
                with sessions() as export_session:
                    export_ledger_many(
                        export_session,
                        approved_batch,
                        approved_token,
                        target_ids=["kingdee_xlsx", "generic_xlsx"],
                        output_dir=Path.cwd() / "exports",
                    )
            except (ApprovalRequired, LookupError, ValueError, FileExistsError) as exc:
                return plain_text(str(exc), 400)
        return RedirectResponse(f"/approvals/{approval_id}", status_code=303)

    @app.get("/vouchers", response_class=HTMLResponse)
    def vouchers_page(request: Request) -> Response:
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.REPORT_READ):
                return permission_denied(session, user, request, Permission.REPORT_READ.value)
            rows = list(session.scalars(select(Voucher).order_by(Voucher.created_at.desc())))
        return templates.TemplateResponse(
            request, "vouchers.html", {"request": request, "rows": rows, "user": user}
        )

    @app.get("/vouchers/{voucher_id}", response_class=HTMLResponse)
    def voucher_detail(request: Request, voucher_id: str) -> Response:
        from uuid import UUID

        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.REPORT_READ):
                return permission_denied(session, user, request, Permission.REPORT_READ.value)
            try:
                row = session.get(Voucher, UUID(voucher_id))
            except ValueError:
                row = None
            if row is None:
                return plain_text("凭证不存在", 404)
            lines = list(
                session.scalars(
                    select(VoucherLine)
                    .where(VoucherLine.voucher_id == row.id)
                    .order_by(VoucherLine.line_no)
                )
            )
            artifacts = list(
                session.scalars(
                    select(ExportArtifact)
                    .where(
                        ExportArtifact.approval_id.in_(
                            select(Approval.id).where(Approval.target_id == str(row.id))
                        )
                    )
                    .order_by(ExportArtifact.target_id)
                )
            )
        return templates.TemplateResponse(
            request,
            "voucher_detail.html",
            {"request": request, "row": row, "lines": lines, "artifacts": artifacts, "user": user},
        )

    @app.get("/vouchers/{voucher_id}/download")
    def voucher_download(
        request: Request, voucher_id: str, target: str = "generic_xlsx"
    ) -> Response:
        from uuid import UUID

        if target not in {"kingdee_xlsx", "generic_xlsx"}:
            return plain_text("不支持的凭证格式", 400)
        denial_batch: str | None = None
        path: Path | None = None
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.VOUCHER_DOWNLOAD):
                return permission_denied(session, user, request, Permission.VOUCHER_DOWNLOAD.value)
            try:
                voucher = session.get(Voucher, UUID(voucher_id))
            except ValueError:
                voucher = None
            if voucher is None:
                return plain_text("凭证不存在", 404)
            artifact = session.scalar(
                select(ExportArtifact)
                .join(Approval, Approval.id == ExportArtifact.approval_id)
                .where(
                    Approval.target_type == "voucher",
                    Approval.target_id == str(voucher.id),
                    ExportArtifact.target_id == target,
                )
                .order_by(ExportArtifact.created_at.desc())
            )
            if artifact is None or not artifact.file_path or not Path(artifact.file_path).is_file():
                denial_batch = f"voucher:{voucher.id}"
            else:
                path = Path(artifact.file_path)
        if denial_batch is not None:
            try:
                with sessions() as denial_session:
                    export_ledger_many(
                        denial_session,
                        denial_batch,
                        None,
                        target_ids=[target],
                        output_dir=Path.cwd() / "exports",
                    )
            except ApprovalRequired as exc:
                return plain_text(str(exc), 403)
            return plain_text("凭证文件不存在", 403)
        assert path is not None
        return FileResponse(path, filename=path.name)

    @app.get("/ask", response_class=HTMLResponse)
    def ask_page(request: Request) -> Response:
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.AI_ASK):
                return permission_denied(session, user, request, Permission.AI_ASK.value)
        return templates.TemplateResponse(
            request, "ask.html", {"request": request, "user": user, "answer": None, "error": None}
        )

    @app.post("/ask", response_class=HTMLResponse)
    def ask_submit(
        request: Request, question: str = Form(...), csrf_token: str = Form(...)
    ) -> Response:
        if csrf_token != request.cookies.get("crosserp_csrf"):
            return plain_text("CSRF 校验失败", 403)
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.AI_ASK):
                return permission_denied(session, user, request, Permission.AI_ASK.value)
            if len(question) > 500:
                return plain_text("问题不能超过 500 个字符", 400)
            now = time.monotonic()
            recent = [item for item in ask_times.get(user.username, []) if now - item < 60]
            if len(recent) >= 6:
                return plain_text("请求过于频繁，请稍后再试", 429)  # noqa: RUF001
            ask_times[user.username] = [*recent, now]
            try:
                answer = ask_agent(question, user_ctx=user.username)
            except RuntimeError as exc:
                return templates.TemplateResponse(
                    request,
                    "ask.html",
                    {"request": request, "user": user, "answer": None, "error": str(exc)},
                    status_code=503,
                )
            append(
                session,
                "user",
                "ai.ask",
                "llm_call",
                hashlib.sha256(question.encode()).hexdigest()[:64],
                None,
                {
                    "question_sha256": hashlib.sha256(question.encode()).hexdigest(),
                    "answer_sha256": hashlib.sha256(answer.text.encode()).hexdigest(),
                    "refused": answer.refused,
                    "citations_count": len(answer.citations),
                },
                actor_user_id=user.id,
                actor_name=user.username,
            )
        return templates.TemplateResponse(
            request, "ask.html", {"request": request, "user": user, "answer": answer, "error": None}
        )

    @app.get("/rows/{table}/{row_id}", response_class=HTMLResponse)
    def row_detail(request: Request, table: str, row_id: str) -> Response:
        from uuid import UUID

        allowed = {
            "profit_snapshot": ProfitSnapshot,
            "order_line": OrderLine,
            "settlement_line": SettlementLine,
            "raw_row": RawRow,
            "issue": Issue,
            "voucher": Voucher,
            "voucher_line": VoucherLine,
            "approval": Approval,
        }
        model = allowed.get(table)
        if model is None:
            return plain_text("行不存在", 404)
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.REPORT_READ):
                return permission_denied(session, user, request, Permission.REPORT_READ.value)
            try:
                row = session.get(model, UUID(row_id))
            except ValueError:
                row = None
            if row is None:
                return plain_text("行不存在", 404)
            values = {column.name: getattr(row, column.name) for column in model.__table__.columns}
        return templates.TemplateResponse(
            request,
            "row_detail.html",
            {"request": request, "table": table, "values": values, "user": user},
        )

    @app.get("/account/tokens", response_class=HTMLResponse)
    def account_tokens(request: Request) -> Response:
        from crosserp.db.schema import ApiToken

        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.AI_ASK):
                return permission_denied(session, user, request, Permission.AI_ASK.value)
            rows = list(
                session.scalars(
                    select(ApiToken)
                    .where(ApiToken.user_id == user.id)
                    .order_by(ApiToken.created_at.desc())
                )
            )
        return templates.TemplateResponse(
            request, "account_tokens.html", {"request": request, "rows": rows, "user": user}
        )

    @app.post("/account/tokens")
    def account_tokens_create(
        request: Request, name: str = Form(...), csrf_token: str = Form(...)
    ) -> Response:
        if csrf_token != request.cookies.get("crosserp_csrf"):
            return plain_text("CSRF 校验失败", 403)
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.AI_ASK):
                return permission_denied(session, user, request, Permission.AI_ASK.value)
            _, plain = create_token(session, user, name=name)
        return HTMLResponse(
            f"<p>Token 只显示这一次: <code>{plain}</code></p><a href='/account/tokens'>返回</a>"
        )

    @app.get("/llm", response_class=HTMLResponse)
    def llm_page(request: Request) -> Response:
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.LLM_MONITOR_READ):
                return permission_denied(session, user, request, Permission.LLM_MONITOR_READ.value)
            rows = list(session.scalars(select(LlmCall).order_by(LlmCall.ts.desc()).limit(1000)))
            stats = summarize(rows)
        return templates.TemplateResponse(
            request, "llm.html", {"request": request, "stats": stats, "user": user}
        )

    @app.get("/llm/calls/{call_id}", response_class=HTMLResponse)
    def llm_call_detail(request: Request, call_id: str) -> Response:
        from uuid import UUID

        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.LLM_MONITOR_READ):
                return permission_denied(session, user, request, Permission.LLM_MONITOR_READ.value)
            row = session.get(LlmCall, UUID(call_id))
            if row is None:
                return plain_text("调用不存在", 404)
        return templates.TemplateResponse(
            request, "llm_call.html", {"request": request, "row": row, "user": user}
        )

    @app.get("/audit", response_class=HTMLResponse)
    def audit_page(
        request: Request,
        actor: str | None = None,
        action: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        page: int = Query(1, ge=1),
    ) -> Response:
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.AUDIT_READ):
                return permission_denied(session, user, request, Permission.AUDIT_READ.value)
            statement = select(AuditLog).order_by(AuditLog.seq.desc())
            if actor:
                statement = statement.where(
                    or_(AuditLog.actor_name == actor, AuditLog.actor_user_id == _try_uuid(actor))
                )
            if action:
                statement = statement.where(AuditLog.action == action)
            if target_type:
                statement = statement.where(AuditLog.target_type == target_type)
            if target_id:
                statement = statement.where(AuditLog.target_id == target_id)
            rows = list(session.scalars(statement.offset((page - 1) * 50).limit(50)))
            items = [
                {"row": row, "diff": diff_json(row.before_json, row.after_json)} for row in rows
            ]
            result = verify_chain(session)
            # 链尾序号直接从记录读取，避免把 UUID 当作序号展示。  # noqa: RUF003
            last = session.scalar(select(AuditLog).order_by(AuditLog.seq.desc()).limit(1))
            last_seq = last.seq if last is not None else 0
            security_head = session.scalar(select(AuditHead).where(AuditHead.chain == "security"))
            from crosserp.audit.security import verify_security_chain

            security_ok = verify_security_chain(session)
            can_export = require(session, user, Permission.AUDIT_EXPORT)
        return templates.TemplateResponse(
            request,
            "audit.html",
            {
                "request": request,
                "items": items,
                "page": page,
                "actor": actor,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "audit_ok": result.ok,
                "audit_checked": result.checked,
                "audit_last_seq": last_seq,
                "security_ok": security_ok,
                "security_last_seq": (
                    _security_last_seq(session)
                    if security_head is not None and security_head.last_id
                    else 0
                ),
                "can_export": can_export,
                "user": user,
            },
        )

    @app.get("/audit/verify")
    def audit_verify_page(request: Request) -> Response:
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.AUDIT_READ):
                return permission_denied(session, user, request, Permission.AUDIT_READ.value)
            business = verify_chain(session)
            from crosserp.audit.security import verify_security_chain

            security_ok = verify_security_chain(session)
        status = (
            f"业务链: {'正常' if business.ok else '损坏'}; "
            f"security 链: {'正常' if security_ok else '损坏'}"
        )
        return plain_text(status, 200)

    @app.get("/audit/export")
    def audit_export_page(request: Request) -> Response:
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.AUDIT_EXPORT):
                return permission_denied(session, user, request, Permission.AUDIT_EXPORT.value)
            fd, output_name = tempfile.mkstemp(prefix="crosserp-audit-", suffix=".zip")
            os.close(fd)
            output = Path(output_name)
            try:
                now = datetime.now(UTC)
                export_audit(
                    session,
                    from_ts=datetime(1970, 1, 1, tzinfo=UTC),
                    to_ts=now + timedelta(seconds=1),
                    fmt="jsonl",
                    output=output,
                    requested_by=user.username,
                )
            except Exception:
                output.unlink(missing_ok=True)
                raise
        return FileResponse(
            output,
            filename="crosserp-audit.zip",
            media_type="application/zip",
            background=BackgroundTask(lambda: output.unlink(missing_ok=True)),
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

    @app.get("/issues/{issue_id}", response_class=HTMLResponse)
    def issue_detail(request: Request, issue_id: str) -> Response:
        from uuid import UUID

        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            issue = session.get(Issue, UUID(issue_id))
            if issue is None:
                return plain_text("异常不存在", 404)
        return HTMLResponse(
            f"<h1>异常详情</h1><p>状态：{issue.status}</p><pre>{issue.detail_json}</pre>"  # noqa: RUF001
        )

    @app.post("/issues/{issue_id}")
    def issue_transition(
        request: Request,
        issue_id: str,
        status: str = Form(...),
        note: str = Form(""),
        csrf_token: str = Form(...),
    ) -> Response:
        from uuid import UUID

        if csrf_token != request.cookies.get("crosserp_csrf"):
            return plain_text("CSRF 校验失败", 403)
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.ISSUE_HANDLE):
                return permission_denied(session, user, request, Permission.ISSUE_HANDLE.value)
            try:
                transition_issue(session, UUID(issue_id), status, note)
            except (ValueError, LookupError) as exc:
                return plain_text(str(exc), 400)
        return RedirectResponse(f"/issues/{issue_id}", status_code=303)

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
            return plain_text("CSRF 校验失败", 403)
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

    @app.get("/admin/users", response_class=HTMLResponse)
    def admin_users(request: Request) -> Response:
        with sessions() as session:
            user = current(request, session)
            if user is None:
                return login_redirect(request)
            if not require(session, user, Permission.USER_MANAGE):
                return permission_denied(session, user, request, Permission.USER_MANAGE.value)
            users = list_users(session)
        return templates.TemplateResponse(
            request, "admin_users.html", {"request": request, "users": users, "user": user}
        )

    @app.post("/admin/users")
    def admin_users_add(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        role: str = Form("viewer"),
        csrf_token: str = Form(...),
    ) -> Response:
        if csrf_token != request.cookies.get("crosserp_csrf"):
            return plain_text("CSRF 校验失败", 403)
        with sessions() as session:
            actor = current(request, session)
            if actor is None:
                return login_redirect(request)
            if not require(session, actor, Permission.USER_MANAGE):
                return permission_denied(session, actor, request, Permission.USER_MANAGE.value)
            if get_by_username(session, username) is not None:
                return plain_text("用户已存在", 400)
            new_user = create_user(session, username=username, password=password, roles=())
            grant_role(session, new_user.id, role, granted_by=actor.id)
            record_security(
                session,
                SecurityEventName.USER_CREATED,
                user_id=actor.id,
                username=username,
                target_user_id=new_user.id,
                detail={"role": role},
            )
        return RedirectResponse("/admin/users", status_code=303)

    return app


def _safe_next(value: str) -> str:
    parsed = urlparse(value or "/")
    if parsed.scheme or parsed.netloc or not value.startswith("/") or value.startswith("//"):
        return "/"
    return value


def _try_uuid(value: str) -> object | None:
    from uuid import UUID

    try:
        return UUID(value)
    except ValueError:
        return None


def _profit_report_payload_hash(session: Session, target_id: str) -> str:
    """利润报表审批使用与 CLI 相同的输入哈希。"""
    store_name, separator, period = target_id.rpartition(":")
    if not separator or not store_name or len(period) != 7:
        raise ValueError("利润报表对象必须是 店铺:YYYY-MM")
    statement = (
        select(ProfitSnapshot.inputs_hash)
        .join(Store, ProfitSnapshot.store_id == Store.id)
        .where(
            ProfitSnapshot.period == period,
            or_(Store.name == store_name, Store.id == _try_uuid(store_name)),
        )
        .order_by(ProfitSnapshot.internal_sku)
    )
    hashes = [str(value) for value in session.scalars(statement)]
    if not hashes:
        raise LookupError(f"找不到利润报表 {target_id}，请先运行 demo 或 profit")  # noqa: RUF001
    return hashlib.sha256("\n".join(hashes).encode("ascii")).hexdigest()


def _security_last_seq(session: Session) -> int:
    row = session.scalar(select(SecurityEvent).order_by(SecurityEvent.seq.desc()).limit(1))
    return row.seq if row is not None else 0
