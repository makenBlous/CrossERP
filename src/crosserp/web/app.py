"""FastAPI 应用工厂。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from crosserp import __version__

# 模板和静态文件相对本文件定位。打包后路径仍然有效。
_WEB_DIR = Path(__file__).parent


def create_app() -> FastAPI:
    """创建只含首页和健康检查的应用。"""
    app = FastAPI()
    templates = Jinja2Templates(directory=_WEB_DIR / "templates")
    app.mount("/static", StaticFiles(directory=_WEB_DIR / "static"), name="static")

    @app.get("/")
    def index(request: Request) -> Response:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"version": __version__},
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app
