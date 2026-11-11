"""检查已注册 JSON 路由是否与 08 OpenAPI 草案一致。"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Any

import yaml

from crosserp.db.session import sqlite_file_url
from crosserp.web.app import create_app


def check_contract(app: Any, spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    draft_paths = spec.get("paths", {})
    generated = app.openapi().get("paths", {})
    for path, operations in generated.items():
        if not path.startswith("/api/v1/"):
            continue
        draft_operations = draft_paths.get(path)
        if draft_operations is None:
            errors.append(f"{path}: 不在 OpenAPI 草案")
            continue
        for method, operation in operations.items():
            if method not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                continue
            draft = draft_operations.get(method)
            if draft is None:
                errors.append(f"{method.upper()} {path}: 不在 OpenAPI 草案")
                continue
            actual_x = operation.get("x-crosserp", {})
            draft_x = draft.get("x-crosserp", {})
            for key in ("permission", "riskTier", "entity", "action"):
                if actual_x.get(key) != draft_x.get(key):
                    errors.append(
                        f"{method.upper()} {path}: x-crosserp.{key} "
                        f"实际={actual_x.get(key)!r} 草案={draft_x.get(key)!r}"
                    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=Path("docs/design/08/openapi-draft.yaml"))
    args = parser.parse_args()
    spec = yaml.safe_load(args.spec.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="crosserp-contract-") as directory:
        app = create_app(sqlite_file_url(Path(directory) / "contract.db"))
        errors = check_contract(app, spec)
        app.state.database_engine.dispose()
    if errors:
        for error in errors:
            print(error)
        return 1
    print("API contract check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
