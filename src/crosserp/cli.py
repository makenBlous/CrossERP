"""CrossERP 命令行入口。"""

from __future__ import annotations

import warnings

import typer
import uvicorn
from sqlalchemy.engine import make_url

from crosserp import __version__
from crosserp.core.errors import DatabaseConfigError
from crosserp.db.dialects import ServerStatus, check_server
from crosserp.db.migrate import ensure_database_directory, upgrade_head
from crosserp.db.session import get_database_url, make_engine
from crosserp.web.app import create_app

app = typer.Typer(add_completion=False)
db_app = typer.Typer(add_completion=False, help="数据库连接与启动自检。")
app.add_typer(db_app, name="db")

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
def init() -> None:
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


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="监听地址。默认只监听本机。"),
    port: int = typer.Option(8000, "--port", help="监听端口。"),
) -> None:
    """启动网页服务。默认只监听 127.0.0.1。"""
    if host == "0.0.0.0":
        typer.echo("对外开放前请配置 HTTPS 和登录（v0.5）")  # noqa: RUF001
    typer.echo(f"CrossERP 服务启动 http://{host}:{port}")
    uvicorn.run(create_app(), host=host, port=port)


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
