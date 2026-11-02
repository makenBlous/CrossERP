"""CrossERP 命令行入口。"""

from __future__ import annotations

import typer

from crosserp import __version__

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
