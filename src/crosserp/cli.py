"""CrossERP 命令行入口。"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import secrets
import time
import unicodedata
import warnings
import webbrowser
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

import typer
import uvicorn
from sqlalchemy import or_, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from crosserp import __version__
from crosserp.approval.service import (
    approve as approve_approval,
)
from crosserp.approval.service import (
    create as create_approval,
)
from crosserp.approval.service import (
    reject as reject_approval,
)
from crosserp.approval.service import (
    submit as submit_approval,
)
from crosserp.audit.checkpoint import create_checkpoint
from crosserp.audit.export import export_audit
from crosserp.audit.log import VerifyResult, append, verify_chain, verify_chain_from_checkpoint
from crosserp.audit.offline_verify import OfflineVerifyError, verify_export
from crosserp.auth.roles import Role
from crosserp.connectors.base import FileConnector
from crosserp.connectors.generic_mapped.mapping import MappingError, load_mapping, mappings_dir
from crosserp.connectors.importer import import_file, record_unreadable_file
from crosserp.connectors.registry import detect, load_connectors
from crosserp.core.enums import ImportStatus, IssueKind
from crosserp.core.errors import (
    DatabaseConfigError,
    DuplicateImportError,
    FileUnreadableError,
    ImportInProgressError,
    UnknownFileTypeError,
)
from crosserp.core.models import ColumnMapping
from crosserp.db.dialects import ServerStatus, check_server
from crosserp.db.migrate import ensure_database_directory, upgrade_head
from crosserp.db.repo.imports import mark_import_batch_failed
from crosserp.db.repo.issues import (
    batch_id_of,
    count_issues_by_kind,
    detail_of,
    get_import_batch,
    list_issues,
)
from crosserp.db.repo.users import (
    create_user,
    get_by_username,
    grant_role,
    list_users,
    revoke_role,
    set_active,
    set_password,
)
from crosserp.db.schema import (
    Approval,
    AppSetting,
    AppUser,
    AuditLog,
    ImportBatch,
    Issue,
    ProfitSnapshot,
    ReconRun,
    Store,
)
from crosserp.db.session import get_database_url, make_engine, session_scope
from crosserp.issues.catalog import definition, render
from crosserp.ledger.write_service import ApprovalRequired
from crosserp.ledger.write_service import export as export_ledger
from crosserp.profit.golden import compare_issues_csv, compare_profit_csv
from crosserp.profit.report_csv import write_report_csv
from crosserp.profit.report_xlsx import write_report_xlsx
from crosserp.profit.service import compute_and_save
from crosserp.recon.engine import reconcile_all
from crosserp.web.app import create_app

app = typer.Typer(add_completion=False)
db_app = typer.Typer(add_completion=False, help="数据库连接与启动自检。")
audit_app = typer.Typer(add_completion=False, help="审计哈希链。")
issues_app = typer.Typer(add_completion=False, help="异常清单。只读。")
imports_app = typer.Typer(add_completion=False, help="导入批次记录。")
approval_app = typer.Typer(add_completion=False, help="审批状态机。")
user_app = typer.Typer(add_completion=False, help="用户与角色管理。")
app.add_typer(db_app, name="db")
app.add_typer(audit_app, name="audit")
app.add_typer(issues_app, name="issues")
app.add_typer(imports_app, name="imports")
app.add_typer(approval_app, name="approval")
app.add_typer(user_app, name="user")

_TYPES = ("auto", "amazon", "shopify", "mapped")
_TYPE_TO_ID = {
    "amazon": "amazon.settlement_v2",
    "shopify": "shopify.payouts",
    "mapped": "generic.mapped",
}
_CURRENCY = re.compile(r"[A-Za-z]{3}")
_SUMMARY_KEYS = ("error", "amount_description", "settlement_id", "diff", "order_id")

_DIALECT_LABELS = {
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "sqlite": "SQLite",
}


def _print_version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_print_version,
        is_eager=True,
        help="打印版本号后退出。",
    ),
) -> None:
    """跨境电商对账工具。"""


@app.command()
def init(
    admin_username: str | None = typer.Option(None, "--admin-username", help="首个管理员用户名。"),
    admin_password_stdin: bool = typer.Option(
        False, "--admin-password-stdin", help="从标准输入读取两行相同的管理员密码。"
    ),
) -> None:
    """建库目录、执行迁移并做启动自检。重复执行无副作用。"""
    url_text = get_database_url()
    engine = None
    try:
        ensure_database_directory(url_text)
        upgrade_head(url_text)
        engine = make_engine(url_text)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", UserWarning)
            status = check_server(engine)
        typer.echo(_report(status))
        for item in caught:
            message = str(item.message)
            if "PostgreSQL" in message:
                typer.echo(f"警告: {message}")
        with session_scope(engine) as session:
            if session.scalar(select(AppUser.id)) is None:
                credentials = _admin_credentials(admin_username, admin_password_stdin)
                if credentials is not None:
                    username, password = credentials
                    user = create_user(
                        session,
                        username=username,
                        password=password,
                        roles=tuple(Role),
                    )
                    session.add(
                        AppSetting(
                            key="solo_mode",
                            value_json=True,
                            updated_by=None,
                            updated_at=datetime.now(UTC),
                        )
                    )
                    append(
                        session,
                        "system",
                        "user.create",
                        "app_user",
                        str(user.id),
                        None,
                        {"username": user.username, "roles": [role.value for role in Role]},
                        reason="初始化首个管理员",
                    )
                    typer.echo(f"已创建管理员 {username}")
        typer.echo("数据库已就绪")
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"数据库初始化失败: {_hide_password(str(exc), url_text)}", err=True)
        raise typer.Exit(code=1) from exc
    finally:
        if engine is not None:
            engine.dispose()


def _admin_credentials(username: str | None, password_stdin: bool) -> tuple[str, str] | None:
    """获取首个管理员凭据; 无终端时保留旧 init 的无交互幂等行为。"""
    import sys

    if username is None and not password_stdin and not sys.stdin.isatty():
        return None
    if username is None:
        username = typer.prompt("管理员用户名").strip()
    if not username:
        raise ValueError("管理员用户名不能为空")
    if password_stdin:
        first = sys.stdin.readline().rstrip("\r\n")
        second = sys.stdin.readline().rstrip("\r\n")
    else:
        first = typer.prompt("管理员密码", hide_input=True)
        second = typer.prompt("再次输入管理员密码", hide_input=True)
    if first != second:
        raise ValueError("两次输入的密码不一致")
    if len(first) < 10:
        raise ValueError("密码至少 10 个字符")
    return username, first


def _user_engine() -> tuple[str, Engine]:
    url = get_database_url()
    upgrade_head(url)
    return url, make_engine(url)


def _read_password(*, stdin: bool) -> str:
    import getpass
    import sys

    value = sys.stdin.readline().rstrip("\r\n") if stdin else getpass.getpass("密码: ")
    if len(value) < 10:
        raise ValueError("密码至少 10 个字符")
    return value


def _actor_user(session: Session, username: str | None) -> AppUser | None:
    if username is None:
        return None
    actor = get_by_username(session, username)
    if actor is None:
        raise ValueError(f"操作者不存在: {username}")
    return actor


@user_app.command("list")
def user_list() -> None:
    """列出用户和角色。"""
    _url, engine = _user_engine()
    try:
        with session_scope(engine) as session:
            for user, roles in list_users(session):
                state = "启用" if user.is_active else "停用"
                typer.echo(f"{user.username}\t{state}\t{','.join(roles)}")
    finally:
        engine.dispose()


@user_app.command("add")
def user_add(
    username: str = typer.Option(..., "--username"),
    role: list[str] | None = typer.Option(None, "--role"),  # noqa: B008
    as_username: str | None = typer.Option(None, "--as"),
    password_stdin: bool = typer.Option(False, "--password-stdin"),
) -> None:
    """添加用户并可授予初始角色。"""
    _url, engine = _user_engine()
    try:
        with session_scope(engine) as session:
            actor = _actor_user(session, as_username)
            if get_by_username(session, username) is not None:
                raise ValueError(f"用户已存在: {username}")
            roles = tuple(Role(item) for item in (role or ()))
            user = create_user(
                session,
                username=username,
                password=_read_password(stdin=password_stdin),
                roles=roles,
                granted_by=None if actor is None else actor.id,
            )
            append(
                session,
                "user" if actor is not None else "system",
                "user.create",
                "app_user",
                str(user.id),
                None,
                {"username": user.username, "roles": [item.value for item in roles]},
                actor_user_id=None if actor is None else actor.id,
                actor_name=None if actor is None else actor.username,
            )
            typer.echo(f"已创建用户 {user.username}")
    except (ValueError, LookupError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@user_app.command("grant")
def user_grant(
    username: str = typer.Option(..., "--username"),
    role: str = typer.Option(..., "--role"),
    as_username: str | None = typer.Option(None, "--as"),
) -> None:
    """授予用户角色。"""
    _change_role(username, role, as_username, grant=True)


@user_app.command("revoke")
def user_revoke(
    username: str = typer.Option(..., "--username"),
    role: str = typer.Option(..., "--role"),
    as_username: str | None = typer.Option(None, "--as"),
) -> None:
    """收回用户角色。"""
    _change_role(username, role, as_username, grant=False)


def _change_role(username: str, role: str, as_username: str | None, *, grant: bool) -> None:
    _url, engine = _user_engine()
    try:
        with session_scope(engine) as session:
            actor = _actor_user(session, as_username)
            user = get_by_username(session, username)
            if user is None:
                raise ValueError(f"用户不存在: {username}")
            role_value = Role(role)
            changed = (
                grant_role(
                    session, user.id, role_value, granted_by=None if actor is None else actor.id
                )
                if grant
                else revoke_role(session, user.id, role_value)
            )
            if not grant and not changed:
                raise ValueError(f"用户没有角色: {role}")
            append(
                session,
                "user" if actor is not None else "system",
                "role.grant" if grant else "role.revoke",
                "app_user",
                str(user.id),
                None,
                {"username": username, "role": role_value.value},
                actor_user_id=None if actor is None else actor.id,
                actor_name=None if actor is None else actor.username,
            )
            typer.echo("角色已更新")
    except (ValueError, LookupError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@user_app.command("disable")
def user_disable(
    username: str = typer.Option(..., "--username"),
    as_username: str | None = typer.Option(None, "--as"),
) -> None:
    _set_user_active(username, as_username, active=False)


@user_app.command("enable")
def user_enable(
    username: str = typer.Option(..., "--username"),
    as_username: str | None = typer.Option(None, "--as"),
) -> None:
    _set_user_active(username, as_username, active=True)


def _set_user_active(username: str, as_username: str | None, *, active: bool) -> None:
    _url, engine = _user_engine()
    try:
        with session_scope(engine) as session:
            actor = _actor_user(session, as_username)
            user = get_by_username(session, username)
            if user is None:
                raise ValueError(f"用户不存在: {username}")
            set_active(session, user.id, active)
            append(
                session,
                "user" if actor is not None else "system",
                "user.enable" if active else "user.disable",
                "app_user",
                str(user.id),
                {"is_active": not active},
                {"is_active": active},
                actor_user_id=None if actor is None else actor.id,
                actor_name=None if actor is None else actor.username,
            )
            typer.echo("用户状态已更新")
    except (ValueError, LookupError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@user_app.command("passwd")
def user_passwd(
    username: str = typer.Option(..., "--username"),
    as_username: str | None = typer.Option(None, "--as"),
    password_stdin: bool = typer.Option(False, "--password-stdin"),
) -> None:
    """重置密码。"""
    _url, engine = _user_engine()
    try:
        with session_scope(engine) as session:
            actor = _actor_user(session, as_username)
            user = get_by_username(session, username)
            if user is None:
                raise ValueError(f"用户不存在: {username}")
            set_password(session, user.id, _read_password(stdin=password_stdin))
            append(
                session,
                "user" if actor is not None else "system",
                "password.changed",
                "app_user",
                str(user.id),
                None,
                {"username": username},
                actor_user_id=None if actor is None else actor.id,
                actor_name=None if actor is None else actor.username,
            )
            typer.echo("密码已更新")
    except (ValueError, LookupError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@app.command()
def serve(
    port: int = typer.Option(8000, "--port", help="监听端口。"),
    host: str = typer.Option("127.0.0.1", "--host", help="监听地址。"),
    i_understand_https: bool = typer.Option(False, "--i-understand-https"),
) -> None:
    """启动网页服务。对外监听必须确认 HTTPS 反向代理。"""
    if host not in {"127.0.0.1", "localhost", "::1"} and not i_understand_https:
        typer.echo("警告：必须放在 HTTPS 反向代理后面，并设置 CROSSERP_COOKIE_SECURE=1。", err=True)  # noqa: RUF001
        raise typer.Exit(code=1)
    typer.echo(f"CrossERP 服务启动 http://{host}:{port}")
    uvicorn.run(create_app(), host=host, port=port)


@dataclass(frozen=True)
class _ImportJob:
    """一个文件的导入参数。demo-import 每个文件可以不同。"""

    path: Path
    file_type: str
    mapping: Path | None
    currency: str | None
    store: str | None


def demo_jobs() -> list[_ImportJob]:
    """合成样本的导入顺序。同一份数据的 csv/xlsx 只导 csv。

    costs.xlsx 与 costs.csv 内容相同。两份都导入会因生效期重叠写出预期外的 PARSE_ERROR。
    fx_rates.xlsx 也是同一份汇率。再导入不会产生新的标准答案。
    fx_rates_missing_eur.csv 是缺汇率场景的替代文件。不是正常汇率表。
    fee_reference.csv 用通用映射导入器写入配送费参考值。
    说明文件和 expected JSON 不是表格。
    """
    root = _synthetic_dir()
    package_maps = mappings_dir()
    shopify_store = "shopify-main"
    return [
        _ImportJob(root / "sku_map.csv", "mapped", package_maps / "template_sku.yaml", None, None),
        _ImportJob(root / "costs.csv", "mapped", package_maps / "template_costs.yaml", None, None),
        _ImportJob(
            root / "fee_reference.csv",
            "mapped",
            package_maps / "template_fee_reference.yaml",
            None,
            None,
        ),
        _ImportJob(
            root / "fx_rates.csv", "mapped", package_maps / "template_fx_rates.yaml", None, None
        ),
        _ImportJob(
            root / "orders.csv",
            "mapped",
            root / "mappings" / "synthetic_orders.yaml",
            None,
            None,
        ),
        _ImportJob(root / "amazon_de_2026-10-01_2026-10-14.tsv", "amazon", None, None, None),
        _ImportJob(root / "amazon_us_2026-10-01_2026-10-14.tsv", "amazon", None, None, None),
        _ImportJob(root / "amazon_us_unbalanced.tsv", "amazon", None, None, None),
        # 合成打款文件没有 Currency 列。币种用 USD。店名与订单表一致。推断。
        _ImportJob(root / "shopify_payout_2026-10-07.csv", "shopify", None, "USD", shopify_store),
        _ImportJob(root / "shopify_payout_2026-10-21.csv", "shopify", None, "USD", shopify_store),
    ]


@app.command("import")
def import_files(
    files: list[Path] | None = typer.Argument(None, help="要导入的文件。可以一次传多个。"),  # noqa: B008
    file_type: str = typer.Option("auto", "--type", help="auto、amazon、shopify 或 mapped。"),
    mapping: Path | None = typer.Option(None, "--mapping", help="mapped 的 YAML 列映射。"),  # noqa: B008
    currency: str | None = typer.Option(None, "--currency", help="文件没有币种时使用。例如 USD。"),
    store: str | None = typer.Option(None, "--store", help="文件没有店铺名时使用。"),
    mark_failed: UUID | None = typer.Option(  # noqa: B008
        None, "--mark-failed", help="把一个 running 批次人工标成失败。"
    ),
) -> None:
    """导入一个或多个文件。每个文件单独一个批次。"""
    if mark_failed is not None:
        if files:
            typer.echo("--mark-failed 不能和文件路径同时使用。", err=True)
            raise typer.Exit(code=1)
        _mark_failed(mark_failed)
        return
    if not files:
        typer.echo("请提供文件路径，或使用 --mark-failed <批次id>。", err=True)  # noqa: RUF001
        raise typer.Exit(code=1)
    jobs = [_ImportJob(path, file_type, mapping, currency, store) for path in files]
    code = _import_jobs(jobs)
    if code != 0:
        raise typer.Exit(code=code)


@issues_app.command("list")
def issues_list(
    kind: str | None = typer.Option(None, "--kind", help="按原因码筛选。"),
    batch: str | None = typer.Option(None, "--batch", help="按导入批次 id 筛选。"),
) -> None:
    """只读列出异常。"""
    if kind is not None and kind not in {item.value for item in IssueKind}:
        allowed = "、".join(item.value for item in IssueKind)
        typer.echo(f"不认识的原因码 {kind}。可用的有 {allowed}。", err=True)
        raise typer.Exit(code=1)
    batch_id: UUID | None = None
    if batch is not None:
        try:
            batch_id = UUID(batch)
        except ValueError as exc:
            typer.echo("批次 id 不是有效的 UUID。", err=True)
            raise typer.Exit(code=1) from exc
    url_text, engine = _open_ready_engine()
    try:
        with session_scope(engine) as session:
            if batch_id is not None and get_import_batch(session, batch_id) is None:
                typer.echo(f"没有这个批次 {batch_id}。", err=True)
                raise typer.Exit(code=1)
            found = list_issues(session, kind=kind, batch_id=batch_id)
            typer.echo(_render_issue_table(found))
            typer.echo(f"共 {len(found)} 条")
    except typer.Exit:
        raise
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"无法列出异常: {_hide_password(str(exc), url_text)}", err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@app.command("demo-import")
def demo_import() -> None:
    """按 sku 映射、成本、汇率、订单、结算/打款导入合成样本。"""
    try:
        jobs = demo_jobs()
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    code = _import_jobs(jobs)
    if code != 0:
        raise typer.Exit(code=code)


@app.command("demo")
def demo_command(
    db: str | None = typer.Option(None, "--db"),
    no_browser: bool = typer.Option(False, "--no-browser"),
    check: bool = typer.Option(False, "--check"),
    port: int = typer.Option(8765, "--port"),
) -> None:
    """在独立演示库中导入样本、对账并计算利润。"""
    started = time.monotonic()
    home = Path(os.environ.get("HOME", str(Path.home())))
    database = db or f"sqlite:///{home / '.crosserp' / 'demo.db'}"
    previous = os.environ.get("CROSSERP_DATABASE_URL")
    os.environ["CROSSERP_DATABASE_URL"] = database
    try:
        if not check and db is None and database.startswith("sqlite:///"):
            database_path = Path(database.removeprefix("sqlite:///"))
            if database_path.exists():
                typer.echo(f"演示数据库已存在，请用 --db 指定新路径: {database_path}", err=True)  # noqa: RUF001
                raise typer.Exit(code=1)
        _import_jobs(demo_jobs())
        _url_text, engine = _open_ready_engine()
        try:
            with session_scope(engine) as session:
                _ensure_demo_user(session)
                results = reconcile_all(session, "2026-10")
                reports = [
                    compute_and_save(session, result.store_id, "2026-10") for result in results
                ]
                total = sum((result.groups_total for result in results), 0)
                matched = sum((result.groups_matched for result in results), 0)
                rate = "无分母" if total == 0 else f"{matched / total:.2%}"
                typer.echo(
                    f"Demo: 组数 {total}，匹配 {matched}，"  # noqa: RUF001
                    f"匹配率 {rate}，利润店铺 {len(reports)}"  # noqa: RUF001
                )
                if check and (total == 0 or matched / total < 0.95):
                    raise typer.Exit(code=1)
        finally:
            engine.dispose()
        typer.echo(f"耗时 {time.monotonic() - started:.2f}s")
        if not check and not no_browser:
            typer.echo(f"启动网页 http://127.0.0.1:{port}")
            webbrowser.open(f"http://127.0.0.1:{port}")
            uvicorn.run(create_app(database), host="127.0.0.1", port=port)
    finally:
        if previous is None:
            os.environ.pop("CROSSERP_DATABASE_URL", None)
        else:
            os.environ["CROSSERP_DATABASE_URL"] = previous


def _ensure_demo_user(session: Session) -> None:
    """演示库首次运行创建 demo 账号，并只打印一次随机密码。"""  # noqa: RUF002
    if session.scalar(select(AppUser.id)) is not None:
        return
    password = secrets.token_urlsafe(18)
    user = create_user(session, username="demo", password=password, roles=tuple(Role))
    session.add(
        AppSetting(
            key="solo_mode",
            value_json=True,
            updated_by=None,
            updated_at=datetime.now(UTC),
        )
    )
    append(
        session,
        "system",
        "user.create",
        "app_user",
        str(user.id),
        None,
        {"username": user.username, "roles": [role.value for role in Role], "demo": True},
        reason="初始化演示管理员",
    )
    typer.echo(f"演示账号 demo，随机密码（仅本次显示）: {password}")  # noqa: RUF001


@app.command("reconcile")
def reconcile_command(
    period: str = typer.Option(..., "--period", help="对账月份，格式 YYYY-MM。"),  # noqa: RUF001
    store: str | None = typer.Option(None, "--store", help="只对指定店铺运行。"),
    as_of: str | None = typer.Option(None, "--as-of", help="预留的截止日，格式 YYYY-MM-DD。"),  # noqa: RUF001
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """运行确定性的订单与结算匹配。"""
    cutoff: date | None = None
    if as_of is not None:
        try:
            cutoff = date.fromisoformat(as_of)
        except ValueError as exc:
            typer.echo("--as-of 必须是 YYYY-MM-DD。", err=True)
            raise typer.Exit(code=1) from exc
    url_text, engine = _open_ready_engine()
    try:
        with session_scope(engine) as session:
            results = reconcile_all(session, period, store, as_of=cutoff)
            if not results:
                typer.echo("没有找到可对账的店铺。")
                return
            if json_output:
                typer.echo(
                    json.dumps(
                        [
                            {
                                "store_id": str(result.store_id),
                                "period": result.period,
                                "groups_total": result.groups_total,
                                "groups_matched": result.groups_matched,
                                "match_rate": None
                                if result.match_rate is None
                                else str(result.match_rate),
                                "unmatched_by_kind": result.unmatched_by_kind,
                                "delayed_count": result.delayed_count,
                                "non_order_lines": result.non_order_lines,
                                "recon_run_id": str(result.run_id),
                            }
                            for result in results
                        ],
                        ensure_ascii=False,
                    )
                )
                return
            for result in results:
                rate = "无分母" if result.match_rate is None else f"{result.match_rate:.2%}"
                reasons = (
                    "、".join(
                        f"{kind}={count}"
                        for kind, count in sorted(result.unmatched_by_kind.items())
                    )
                    or "无"
                )
                overcharge = (
                    "、".join(
                        f"{currency}={amount}"
                        for currency, amount in sorted(
                            (result.overcharge_by_currency or {}).items()
                        )
                    )
                    or "无"
                )
                typer.echo(
                    f"店铺 {result.store_id}: 组数 {result.groups_total}，"  # noqa: RUF001
                    f"匹配 {result.groups_matched}，匹配率 {rate}，"  # noqa: RUF001
                    f"未匹配原因 {reasons}，待下期 {result.delayed_count}，"  # noqa: RUF001
                    f"多收费 {overcharge}，拒付 {result.chargeback_count}，"  # noqa: RUF001
                    f"非订单行 {result.non_order_lines}"
                )
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"对账失败: {_hide_password(str(exc), url_text)}", err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@app.command("profit")
def profit_command(
    period: str = typer.Option(..., "--period", help="利润月份，格式 YYYY-MM。"),  # noqa: RUF001
    store: str | None = typer.Option(None, "--store", help="只计算指定店铺。"),
    out: Path | None = typer.Option(None, "--out"),  # noqa: B008
    csv_dir: Path | None = typer.Option(None, "--csv-dir"),  # noqa: B008
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    """计算确定性的 SKU 利润摘要。"""
    url_text, engine = _open_ready_engine()
    try:
        with session_scope(engine) as session:
            if (
                session.scalar(
                    select(ReconRun.id).where(ReconRun.period == period, ReconRun.status == "done")
                )
                is None
            ):
                typer.echo("尚未有当前对账结果，先运行对账。")  # noqa: RUF001
                reconcile_all(session, period, store)
            statement = select(Store).order_by(Store.platform, Store.name)
            if store is not None:
                statement = statement.where(Store.name == store)
            reports = [
                compute_and_save(session, item.id, period) for item in session.scalars(statement)
            ]
            if out is not None:
                write_report_xlsx(
                    session, period=period, reports=reports, path=out, overwrite=overwrite
                )
            if csv_dir is not None:
                write_report_csv(session, period=period, directory=csv_dir)
            if not reports:
                typer.echo("没有找到可计算利润的店铺。")
                return
            for report in reports:
                profit = "缺成本/汇率" if report.store_profit is None else str(report.store_profit)
                cny = "缺汇率" if report.store_profit_cny is None else str(report.store_profit_cny)
                typer.echo(
                    f"店铺 {report.store_id}: SKU {len(report.sku_profits)} 个，"  # noqa: RUF001
                    f"原币利润 {profit}，人民币利润 {cny}，未分摊费用 {report.unallocated_fees}，"  # noqa: RUF001
                    f"广告 {'已含' if report.ads_included else '未含'}"
                )
                for item in report.sku_profits[:10]:
                    value = "缺成本/汇率" if item.profit is None else str(item.profit)
                    typer.echo(f"  {item.internal_sku}: {value} ({item.status})")
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"利润计算失败: {_hide_password(str(exc), url_text)}", err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@app.command("check-golden")
def check_golden_command(
    period: str = typer.Option(..., "--period", help="利润月份，格式 YYYY-MM。"),  # noqa: RUF001
    expected: Path = typer.Option(..., "--expected", exists=True, readable=True),  # noqa: B008
    issues: Path | None = typer.Option(None, "--issues", exists=True, readable=True),  # noqa: B008
    store: str | None = typer.Option(None, "--store", help="只比对指定店铺。"),
    report_md: Path | None = typer.Option(None, "--report-md"),  # noqa: B008
) -> None:
    """逐格检查利润 golden CSV。"""
    url_text, engine = _open_ready_engine()
    try:
        with session_scope(engine) as session:
            result = compare_profit_csv(session, period, expected, store)
            issue_result = None if issues is None else compare_issues_csv(session, issues)
        typer.echo(
            f"{result.matched_rows}/{result.compared_rows} 行完全一致，"  # noqa: RUF001
            + f"reference-only {result.reference_only_rows} 行，"  # noqa: RUF001
            + f"差异 {len(result.diffs)}，缺行 {len(result.missing_rows)}"  # noqa: RUF001
        )
        if result.missing_rows:
            typer.echo("缺行: " + "、".join(result.missing_rows), err=True)
        for diff in result.diffs:
            typer.echo(
                f"差异 {diff.key} {diff.column}: 期望 {diff.expected}，实际 {diff.actual}",  # noqa: RUF001
                err=True,
            )
        if issue_result is not None:
            typer.echo(
                f"异常 {issue_result.matched}/{issue_result.expected} 条一致，"  # noqa: RUF001
                f"漏报 {len(issue_result.missing)}，多报 {len(issue_result.extra)}"  # noqa: RUF001
            )
        if report_md is not None:
            report_md.parent.mkdir(parents=True, exist_ok=True)
            report_md.write_text(
                "# Golden 利润比对\n\n"
                + f"- 完全一致：{result.matched_rows}/{result.compared_rows}\n"  # noqa: RUF001
                + f"- reference-only：{result.reference_only_rows}\n"  # noqa: RUF001
                + f"- 差异：{len(result.diffs)}\n"  # noqa: RUF001
                + f"- 缺行：{len(result.missing_rows)}\n",  # noqa: RUF001
                encoding="utf-8",
            )
        if not result.ok or (issue_result is not None and not issue_result.ok):
            raise typer.Exit(code=1)
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


def _import_jobs(jobs: list[_ImportJob]) -> int:
    """导入多个文件。返回退出码。一个失败不影响其他文件。"""
    _reject_bad_flags(jobs)
    url_text, engine = _open_ready_engine()
    connectors = _connectors()
    loaded: dict[Path, ColumnMapping] = {}
    rows: list[list[str]] = []
    failed = False
    try:
        for job in jobs:
            if not _import_one(engine, connectors, loaded, job, rows):
                failed = True
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        return 1
    except Exception as exc:
        typer.echo(f"导入失败: {_hide_password(str(exc), url_text)}", err=True)
        return 1
    finally:
        engine.dispose()
    if rows:
        typer.echo(
            _render_table(["文件名", "连接器", "数据行数", "成功行数", "异常数", "批次"], rows)
        )
    return 1 if failed else 0


def _import_one(
    engine: Engine,
    connectors: list[FileConnector],
    loaded: dict[Path, ColumnMapping],
    job: _ImportJob,
    rows: list[list[str]],
) -> bool:
    """导入一个文件。成功或重复返回 True。其他失败返回 False。"""
    try:
        connector = _connector_for(job.path, job.file_type, connectors)
        mapping = _mapping_for(job, loaded)
    except (UnknownFileTypeError, MappingError, FileUnreadableError) as exc:
        if not job.path.is_file():
            message = f"无法读取文件 {job.path.name}。文件不存在或不是普通文件。"
            with session_scope(engine) as session:
                result = record_unreadable_file(
                    session,
                    job.path,
                    connector_id="unknown",
                    connector_version="0",
                    mapping=None,
                    message=message,
                )
            typer.echo(message, err=True)
            rows.append([job.path.name, "unknown", "0", "0", "失败", str(result.batch_id)])
            return False
        typer.echo(_file_error(job.path, exc), err=True)
        rows.append([job.path.name, "-", "0", "0", "失败", "-"])
        return False
    try:
        with session_scope(engine) as session:
            result = import_file(session, job.path, connector, mapping)
            counts = count_issues_by_kind(session, result.batch_id)
    except DuplicateImportError as exc:
        typer.echo(f"警告: {job.path.name} 已导入过（{exc.imported_at}），跳过")  # noqa: RUF001
        return True
    except ImportInProgressError as exc:
        typer.echo(f"{job.path.name}: {exc}", err=True)
        rows.append([job.path.name, connector.id, "0", "0", "失败", "-"])
        return False
    except FileUnreadableError as exc:
        typer.echo(str(exc), err=True)
        rows.append([job.path.name, connector.id, "0", "0", "失败", "-"])
        return False
    except Exception as exc:
        typer.echo(f"{job.path.name}: {exc}", err=True)
        rows.append([job.path.name, connector.id, "0", "0", "失败", "-"])
        return False
    success = max(result.row_count - result.error_count, 0)
    if result.status is ImportStatus.FAILED:
        typer.echo(f"{job.path.name}: {result.message or '整批导入失败'}", err=True)
        rows.append(
            [
                job.path.name,
                connector.id,
                str(result.row_count),
                str(success),
                "失败",
                str(result.batch_id),
            ]
        )
        return False
    rows.append(
        [
            job.path.name,
            connector.id,
            str(result.row_count),
            str(success),
            _format_counts(counts),
            str(result.batch_id),
        ]
    )
    return True


@imports_app.command("list")
def imports_list() -> None:
    """列出导入批次及失败、重试信息。"""
    url_text, engine = _open_ready_engine()
    try:
        with session_scope(engine) as session:
            batches = session.scalars(
                select(ImportBatch).order_by(ImportBatch.imported_at.desc())
            ).all()
            rows = [
                [
                    _format_time(batch.imported_at),
                    batch.file_name,
                    batch.status,
                    "-" if batch.file_sha256 is None else batch.file_sha256[:8],
                    "-" if batch.failure_reason is None else batch.failure_reason,
                    "-" if batch.retry_of_batch_id is None else str(batch.retry_of_batch_id),
                    str(batch.id),
                ]
                for batch in batches
            ]
            typer.echo(
                _render_table(
                    ["时间", "文件", "状态", "sha256", "失败原因", "重试自", "批次"], rows
                )
            )
            typer.echo(f"共 {len(rows)} 条")
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@approval_app.command("request")
def approval_request(
    target: str = typer.Option(..., "--target", help="对象，格式 profit_report:<店铺>:<期间>。"),  # noqa: RUF001
    as_name: str = typer.Option(..., "--as", help="提交人姓名。"),
    payload_hash: str | None = typer.Option(None, "--payload-hash", help="对象当前内容哈希。"),
) -> None:
    """创建并提交一张审批单。"""
    target_type, target_id = _parse_approval_target(target)
    url_text, engine = _open_ready_engine()
    try:
        with session_scope(engine) as session:
            current_hash = payload_hash
            if target_type == "profit_report" and current_hash is None:
                current_hash = _profit_report_payload_hash(session, target_id)
            row = create_approval(
                session,
                target_type=target_type,
                target_id=target_id,
                requested_by=as_name,
                payload_hash=current_hash,
            )
            submit_approval(session, row, actor=as_name)
            typer.echo(f"审批单已提交：{row.id}（状态 {row.state}）")  # noqa: RUF001
    except (LookupError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@approval_app.command("list")
def approval_list() -> None:
    """列出审批单，不显示任何 token 明文。"""  # noqa: RUF002
    url_text, engine = _open_ready_engine()
    try:
        with session_scope(engine) as session:
            rows = [
                [
                    str(row.id),
                    row.target_type,
                    row.target_id,
                    row.state,
                    row.requested_by,
                    row.approver or "-",
                    _format_time(row.requested_at),
                    "是" if row.used_at is not None else "否",
                ]
                for row in session.scalars(
                    select(Approval).order_by(Approval.requested_at, Approval.id)
                )
            ]
            typer.echo(
                _render_table(
                    [
                        "审批单",
                        "对象类型",
                        "对象",
                        "状态",
                        "提交人",
                        "审批人",
                        "申请时间",
                        "已使用",
                    ],
                    rows,
                )
            )
            typer.echo(f"共 {len(rows)} 条")
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@approval_app.command("approve")
def approval_approve(
    approval_id: UUID = typer.Argument(..., help="审批单 UUID。"),  # noqa: B008
    as_name: str = typer.Option(..., "--as", help="审批人姓名。"),
) -> None:
    """批准并只打印一次性 token。"""
    url_text, engine = _open_ready_engine()
    try:
        with session_scope(engine) as session:
            row = session.get(Approval, approval_id)
            if row is None:
                raise LookupError(f"审批单不存在 {approval_id}")
            token = approve_approval(session, row, approver=as_name)
            typer.echo(f"审批已通过：{row.id}")  # noqa: RUF001
            typer.echo(f"一次性 token（只显示这一次）：{token}")  # noqa: RUF001
    except (LookupError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@approval_app.command("reject")
def approval_reject(
    approval_id: UUID = typer.Argument(..., help="审批单 UUID。"),  # noqa: B008
    as_name: str = typer.Option(..., "--as", help="审批人姓名。"),
    comment: str | None = typer.Option(None, "--comment", help="驳回原因，必填。"),  # noqa: RUF001
) -> None:
    """驳回审批单，必须留下原因。"""  # noqa: RUF002
    url_text, engine = _open_ready_engine()
    try:
        with session_scope(engine) as session:
            row = session.get(Approval, approval_id)
            if row is None:
                raise LookupError(f"审批单不存在 {approval_id}")
            reject_approval(session, row, approver=as_name, comment=comment or "")
            typer.echo(f"审批已驳回：{row.id}")  # noqa: RUF001
    except (LookupError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@app.command("export")
def export_command(
    target: str = typer.Option(..., "--target", help="写出目标，目前只有 xlsx。"),  # noqa: RUF001
    batch: str = typer.Option(..., "--batch", help="对象，格式 profit_report:<店铺>:<期间>。"),  # noqa: RUF001
    token: str | None = typer.Option(None, "--token", help="审批批准后打印的一次性 token。"),
) -> None:
    """通过唯一写出口导出已批准的报表。"""
    url_text, engine = _open_ready_engine()
    try:
        with session_scope(engine) as session:
            artifact = export_ledger(session, batch, target, token)
            typer.echo(f"导出成功：{artifact.file_path}")  # noqa: RUF001
            typer.echo(f"sha256：{artifact.sha256}")  # noqa: RUF001
    except ApprovalRequired as exc:
        typer.echo(f"没有有效审批：{exc}", err=True)  # noqa: RUF001
        raise typer.Exit(code=1) from exc
    except (LookupError, ValueError, FileExistsError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


def _parse_approval_target(value: str) -> tuple[str, str]:
    target_type, separator, target_id = value.partition(":")
    if not separator or not target_type.strip() or not target_id.strip():
        raise ValueError("--target 格式必须是 类型:对象，例如 profit_report:店铺:2026-10")  # noqa: RUF001
    return target_type.strip(), target_id.strip()


def _profit_report_payload_hash(session: Session, target_id: str) -> str:
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


def _try_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None


def _mark_failed(batch_id: UUID) -> None:
    url_text, engine = _open_ready_engine()
    try:
        with session_scope(engine) as session:
            batch = session.get(ImportBatch, batch_id)
            if batch is None:
                typer.echo(f"没有这个批次 {batch_id}。", err=True)
                raise typer.Exit(code=1)
            mark_import_batch_failed(
                session,
                batch,
                failure_code="MANUAL_MARK_FAILED",
                failure_reason="用户确认导入进程已中断，手动标记失败。",  # noqa: RUF001
            )
            append(
                session,
                actor_type="system",
                action="import_failed",
                target_type="import_batch",
                target_id=str(batch.id),
                before={"status": ImportStatus.RUNNING.value},
                after={"status": batch.status, "failure_code": batch.failure_code},
                reason="手动标记导入失败",
                self_approved=False,
            )
            typer.echo(f"批次 {batch.id} 已标记失败")
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


def _reject_bad_flags(jobs: list[_ImportJob]) -> None:
    bad_types = sorted({job.file_type for job in jobs} - set(_TYPES))
    if bad_types:
        names = "、".join(bad_types)
        typer.echo(f"不认识的 --type {names}。可用 auto、amazon、shopify、mapped。", err=True)
        raise typer.Exit(code=1)
    for job in jobs:
        if job.currency is not None and _CURRENCY.fullmatch(job.currency.strip()) is None:
            typer.echo(f"币种必须是 3 位字母。收到 {job.currency}。", err=True)
            raise typer.Exit(code=1)
        if job.store is not None and (not job.store.strip() or len(job.store.strip()) > 255):
            typer.echo("店铺名不能为空。也不能超过 255 个字符。", err=True)
            raise typer.Exit(code=1)


def _connectors() -> list[FileConnector]:
    """优先用入口点。指定解释器未安装入口点时直接加载内置连接器。"""
    found = load_connectors()
    if found:
        return found
    loaded: list[FileConnector] = []
    modules = (
        ("crosserp.connectors.amazon_settlement_v2", "AmazonSettlementV2Connector"),
        ("crosserp.connectors.shopify_payouts", "ShopifyPayoutsConnector"),
        ("crosserp.connectors.generic_mapped", "GenericMappedConnector"),
    )
    for module_name, class_name in modules:
        try:
            module = importlib.import_module(module_name)
            created = getattr(module, class_name)()
        except (ImportError, AttributeError):
            continue
        if isinstance(created, FileConnector):
            loaded.append(created)
    return loaded


def _connector_for(path: Path, file_type: str, connectors: list[FileConnector]) -> FileConnector:
    if file_type == "auto":
        try:
            found = detect(path, connectors)
        except UnknownFileTypeError as exc:
            raise UnknownFileTypeError(
                exc.path,
                f"{exc.detail}可用的 --type 是 amazon、shopify、mapped。",
            ) from exc
        return _fresh(found)
    wanted = _TYPE_TO_ID[file_type]
    matches = [item for item in connectors if item.id == wanted]
    if len(matches) != 1:
        names = "、".join(item.id for item in connectors) or "无"
        raise UnknownFileTypeError(path.name, f"没有可用的 {wanted}。已加载 {names}。")
    return _fresh(matches[0])


def _fresh(connector: FileConnector) -> FileConnector:
    created = type(connector)()
    if not isinstance(created, FileConnector):
        raise TypeError(f"无法创建连接器 {connector.id}")
    return created


def _mapping_for(job: _ImportJob, loaded: dict[Path, ColumnMapping]) -> ColumnMapping | None:
    if job.file_type == "mapped" and job.mapping is None:
        raise MappingError("必须显式提供映射文件。请使用 --type mapped --mapping。")
    mapping: ColumnMapping | None = None
    if job.mapping is not None:
        if not job.mapping.is_file():
            raise MappingError(f"找不到映射文件 {job.mapping}。")
        key = job.mapping.resolve()
        if key not in loaded:
            loaded[key] = load_mapping(job.mapping)
        mapping = loaded[key]
    return _with_overrides(mapping, job.currency, job.store)


def _with_overrides(
    mapping: ColumnMapping | None,
    currency: str | None,
    store: str | None,
) -> ColumnMapping | None:
    if currency is None and store is None:
        return mapping
    base = ColumnMapping() if mapping is None else mapping
    defaults = dict(base.defaults)
    if currency is not None:
        defaults["currency"] = currency.strip().upper()
    if store is not None:
        defaults["store_name"] = store.strip()
    return base.model_copy(update={"defaults": defaults})


def _file_error(path: Path, exc: Exception) -> str:
    text = str(exc)
    if path.name in text:
        return text
    return f"{path.name}: {text}"


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "0"
    return " ".join(f"{kind}={counts[kind]}" for kind in sorted(counts))


def _synthetic_dir() -> Path:
    packaged = Path(__file__).parent / "demo" / "samples" / "synthetic"
    cwd_samples = Path.cwd() / "samples" / "synthetic"
    for item in (packaged, cwd_samples):
        if (item / "sku_map.csv").is_file():
            return item
    raise FileNotFoundError("找不到 samples/synthetic。请在仓库根目录运行 crosserp demo-import。")


def _open_ready_engine() -> tuple[str, Engine]:
    url_text = get_database_url()
    try:
        ensure_database_directory(url_text)
        upgrade_head(url_text)
        return url_text, make_engine(url_text)
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"数据库初始化失败: {_hide_password(str(exc), url_text)}", err=True)
        raise typer.Exit(code=1) from exc


def _render_issue_table(found: list[Issue]) -> str:
    rows: list[list[str]] = []
    for item in found:
        detail = detail_of(item)
        source = detail.get("source_file")
        file_name = Path(str(source)).name if isinstance(source, str) and source else "-"
        row_no = detail.get("row_no")
        batch = batch_id_of(item) or "-"
        rows.append(
            [
                _format_time(item.created_at),
                item.kind,
                definition(item.kind).name_zh,
                item.severity,
                item.status,
                file_name,
                "-" if row_no is None else str(row_no),
                batch,
                render(item, detail),
            ]
        )
    return _render_table(
        ["时间", "原因码", "中文名称", "严重程度", "状态", "文件", "行号", "批次", "说明"], rows
    )


def _issue_summary(detail: dict[str, object]) -> str:
    parts: list[str] = []
    for key in _SUMMARY_KEYS:
        if key not in detail:
            continue
        text = str(detail[key]).replace("\n", " ")
        if len(text) > 80:
            text = text[:77] + "..."
        parts.append(text if key == "error" else f"{key}={text}")
    return " ".join(parts)


def _format_time(value: datetime) -> str:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _display_width(text: str) -> int:
    width = 0
    for char in text:
        width += 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
    return width


def _render_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [_display_width(cell) for cell in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], _display_width(cell))

    def line(cells: list[str]) -> str:
        padded = [
            cell + " " * (widths[index] - _display_width(cell)) for index, cell in enumerate(cells)
        ]
        return "  ".join(padded).rstrip()

    separator = "  ".join("-" * width for width in widths)
    body = [line(row) for row in rows]
    return "\n".join([line(headers), separator, *body])


def _report(status: ServerStatus) -> str:
    label = _DIALECT_LABELS.get(status.dialect, status.dialect)
    version = status.version
    if status.dialect == "mysql" and not version.upper().startswith("MYSQL"):
        version = f"MySQL {version}"
    elif status.dialect == "postgresql" and not version.upper().startswith("POSTGRESQL"):
        version = f"PostgreSQL {version}"
    lines = [
        f"数据库类型: {label}",
        f"版本: {version}",
    ]
    if status.dialect == "mysql":
        lines.append(f"字符集 {status.charset} OK")
        lines.append("STRICT 模式 OK")
    lines.append("自检: OK")
    return "\n".join(lines)


def _hide_password(message: str, url_text: str) -> str:
    password = make_url(url_text).password
    if password:
        return message.replace(password, "***")
    return message


@audit_app.command("verify")
def audit_verify(
    from_checkpoint: UUID | None = typer.Option(None, "--from-checkpoint"),  # noqa: B008
) -> None:
    """校验审计哈希链。完整时退出码 0。发现改动或删除时退出码 1。"""
    url_text = get_database_url()
    engine = None
    result: VerifyResult | None = None
    try:
        ensure_database_directory(url_text)
        upgrade_head(url_text)
        engine = make_engine(url_text)
        with session_scope(engine) as session:
            result = (
                verify_chain_from_checkpoint(session, from_checkpoint)
                if from_checkpoint is not None
                else verify_chain(session)
            )
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"审计链校验失败: {_hide_password(str(exc), url_text)}", err=True)
        raise typer.Exit(code=1) from exc
    finally:
        if engine is not None:
            engine.dispose()
    if result is None:
        raise typer.Exit(code=1)
    if result.ok:
        typer.echo(f"审计链完整：{result.checked} 条")  # noqa: RUF001
        return
    bad = result.first_bad_id or "未知"
    reason = result.reason or "哈希链校验失败"
    typer.echo(f"审计链损坏：第一条坏记录 {bad}。{reason}", err=True)  # noqa: RUF001
    raise typer.Exit(code=1)


@audit_app.command("tail")
def audit_tail(
    count: int = typer.Option(20, "-n", min=1, max=200, help="显示最近多少条。"),
) -> None:
    """按 Asia/Shanghai 时间显示最近审计记录。"""
    from zoneinfo import ZoneInfo

    url_text, engine = _open_ready_engine()
    try:
        with session_scope(engine) as session:
            rows = list(
                session.scalars(select(AuditLog).order_by(AuditLog.seq.desc()).limit(count))
            )
            for row in rows:
                timestamp = row.ts.astimezone(ZoneInfo("Asia/Shanghai"))
                actor = row.actor_name or row.actor_user_id or row.actor_type
                reason = "" if row.reason is None else f" 原因: {row.reason}"
                typer.echo(
                    f"{timestamp:%Y-%m-%d %H:%M:%S %z} actor={actor} "
                    f"action={row.action} target={row.target_type}:{row.target_id}{reason}"
                )
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@audit_app.command("export")
def audit_export_command(
    from_date: str = typer.Option(..., "--from", help="上海时区起始日期 YYYY-MM-DD。"),
    to_date: str = typer.Option(..., "--to", help="上海时区结束日期 YYYY-MM-DD（含当天）。"),  # noqa: RUF001
    fmt: str = typer.Option("jsonl", "--format", help="jsonl 或 csv。"),
    out: Path = typer.Option(..., "--out"),  # noqa: B008
    requested_by: str = typer.Option("system", "--as", help="导出申请人名称。"),
) -> None:
    """导出可离线校验的审计包。"""
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    try:
        timezone = ZoneInfo("Asia/Shanghai")
        start = datetime.fromisoformat(from_date).replace(tzinfo=timezone).astimezone(UTC)
        end_local = datetime.fromisoformat(to_date).replace(tzinfo=timezone) + timedelta(days=1)
        end = end_local.astimezone(UTC)
    except ValueError as exc:
        typer.echo(f"日期必须是 YYYY-MM-DD: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    url_text, engine = _open_ready_engine()
    try:
        with session_scope(engine) as session:
            row = export_audit(
                session,
                from_ts=start,
                to_ts=end,
                fmt=fmt,
                output=out,
                requested_by=requested_by,
            )
            typer.echo(f"审计包已导出：{out}")  # noqa: RUF001
            typer.echo(f"记录数：{row.row_count}，sha256：{row.file_sha256}")  # noqa: RUF001
    except (ValueError, FileExistsError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@audit_app.command("verify-export")
def audit_verify_export(path: Path = typer.Argument(..., exists=True, readable=True)) -> None:  # noqa: B008
    """不连接数据库，离线校验审计包。"""  # noqa: RUF002
    try:
        verify_export(path)
    except OfflineVerifyError as exc:
        typer.echo(f"审计包校验失败：{exc}", err=True)  # noqa: RUF001
        raise typer.Exit(code=1) from exc
    typer.echo("审计包校验通过")


@audit_app.command("checkpoint")
def audit_checkpoint(reason: str = typer.Option(..., "--reason", help="检查点原因。")) -> None:
    """记录审计链检查点，不删除任何记录。"""  # noqa: RUF002
    url_text, engine = _open_ready_engine()
    try:
        with session_scope(engine) as session:
            row = create_checkpoint(session, reason=reason)
            typer.echo(f"检查点已创建：{row.id}")  # noqa: RUF001
    except (ValueError, DatabaseConfigError) as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()


@db_app.command("check")
def db_check() -> None:
    """打印数据库类型、版本和启动自检结果。"""
    url_text = get_database_url()
    engine = None
    try:
        engine = make_engine(url_text)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", UserWarning)
            status = check_server(engine)
        typer.echo(_report(status))
        for item in caught:
            message = str(item.message)
            if "PostgreSQL" in message:
                typer.echo(f"警告: {message}")
    except DatabaseConfigError as exc:
        typer.echo(_hide_password(str(exc), url_text), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"无法连接数据库: {_hide_password(str(exc), url_text)}", err=True)
        raise typer.Exit(code=1) from exc
    finally:
        if engine is not None:
            engine.dispose()
