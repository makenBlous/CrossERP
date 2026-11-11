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
    return json.loads((Path(__file__).parent / "role_templates.json").read_text(encoding="utf-8"))


__all__ = ["load_catalog", "load_role_templates"]
