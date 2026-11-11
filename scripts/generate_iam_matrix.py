"""生成 IAM 21 角色与 API 路由权限矩阵。"""

from __future__ import annotations

import json
from pathlib import Path

from crosserp.api.routers.iam import _ROUTES
from crosserp.iam.catalog import load_role_templates

LEGACY = {
    "admin": set(load_role_templates().get("owner_manager", ())),
    "operator": {"report:read", "integration:import", "agent_tool:read"},
    "finance": {"report:read", "approval:approve", "journal_entry:export"},
    "viewer": {"report:read", "agent_tool:read"},
    "auditor": {"report:read", "audit_log:read", "audit_log:export"},
}
SELF_SERVICE = {"user:read", "user:write"}
templates = load_role_templates()
roles = {key: set(value) | SELF_SERVICE for key, value in templates.items()}
LEGACY = {key: permissions | SELF_SERVICE for key, permissions in LEGACY.items()}
roles.update(LEGACY)
assert len(roles) == 21, len(roles)
rows = []
for role, permissions in sorted(roles.items()):
    for method, path, _entity, action, permission, risk, _status in _ROUTES:
        human = (
            200 if permission in {"public", "authenticated"} or permission in permissions else 404
        )
        ai = 403 if risk == "critical" else human
        rows.append(
            {
                "role": role,
                "method": method,
                "path": path,
                "action": action,
                "permission": permission,
                "riskTier": risk,
                "human": human,
                "aiOn": ai,
                "aiOff": ai,
            }
        )
out = Path(__file__).parents[1] / "tests" / "guard" / "data" / "iam_route_matrix.json"
out.write_text(
    json.dumps(
        {"source": "role_templates.json + iam.py _ROUTES", "rows": rows},
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(f"generated {len(rows)} rows for {len(roles)} roles")
