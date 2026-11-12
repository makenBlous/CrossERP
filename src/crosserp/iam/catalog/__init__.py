# mypy: ignore-errors
# ruff: noqa

"""前端权限目录的后端快照。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_catalog() -> list[dict[str, Any]]:
    return json.loads(
        (Path(__file__).parent / "permission_points.json").read_text(encoding="utf-8")
    )


def load_role_templates() -> dict[str, list[str]]:
    raw = _load_role_template_file()
    return {key: value for key, value in raw.items() if key != "_dataScopes"}


def load_role_template_scopes() -> dict[str, list[str]]:
    raw = _load_role_template_file()
    scopes = raw["_dataScopes"]
    if not isinstance(scopes, dict):
        raise ValueError("role_templates.json 的 _dataScopes 必须是对象")
    return {str(key): [str(item) for item in value] for key, value in scopes.items()}


def _load_role_template_file() -> dict[str, Any]:
    return json.loads((Path(__file__).parent / "role_templates.json").read_text(encoding="utf-8"))


__all__ = ["load_catalog", "load_role_template_scopes", "load_role_templates"]
