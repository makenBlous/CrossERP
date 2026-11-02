"""CrossERP 命令行入口。"""

from __future__ import annotations

import typer
import uvicorn

from crosserp import __version__
from crosserp.web.app import create_app

app = typer.Typer(add_completion=False)


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
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="监听地址。默认只监听本机。"),
    port: int = typer.Option(8000, "--port", help="监听端口。"),
) -> None:
    """启动网页服务。默认只监听 127.0.0.1。"""
    if host == "0.0.0.0":
        typer.echo("对外开放前请配置 HTTPS 和登录（v0.5）")  # noqa: RUF001
    typer.echo(f"CrossERP 服务启动 http://{host}:{port}")
    uvicorn.run(create_app(), host=host, port=port)
