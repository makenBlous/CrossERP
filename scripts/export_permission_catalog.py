# ruff: noqa

"""从前端权限目录导出后端入库快照。

脚本只解析仓库中的声明式 permissionCatalog 组成部分，不执行前端代码，因而可在
后端 CI 中离线运行。前端目录结构变化时，生成文件的校验哈希会变化。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "frontend" / "src" / "config" / "permissions.ts"
TARGET = ROOT / "src" / "crosserp" / "iam" / "catalog" / "permission_points.json"
ROLE_TARGET = ROOT / "src" / "crosserp" / "iam" / "catalog" / "role_templates.json"


def export(source: Path = SOURCE, target: Path | None = TARGET) -> list[dict[str, object]]:
    text = source.read_text(encoding="utf-8")
    action_start = text.index("const legacyActionLabels")
    doc_start = text.index("const docTypes")
    catalog_start = text.index("export const permissionCatalog")
    action_block = text[action_start:doc_start]
    doc_block = text[doc_start:catalog_start]
    actions = re.findall(r"^  ([a-z]+): \['([^']+)', '([^']+)'\]", action_block, re.M)
    docs = re.findall(r"^  \['([^']+)', '([^']+)', '([^']+)', '([^']+)'\]", doc_block, re.M)
    points: list[dict[str, object]] = []
    for doc_type, label, module, erpnext in docs:
        for action, label_zh, label_en in actions:
            points.append(
                {
                    "key": f"{doc_type}:{action}",
                    "labelZh": f"{label}{label_zh}",
                    "labelEn": f"{erpnext} {label_en}",
                    "module": module,
                    "kind": "menu" if action == "read" else "action",
                    "sensitive": doc_type in {"salary_slip", "payment_entry", "permission"},
                    "dataScopeRuleTypes": [
                        "all",
                        "store",
                        "department",
                        "self",
                        "owner",
                        "warehouse",
                        "amount",
                    ],
                    "erpnextRef": erpnext,
                }
            )
    # permissionCatalog.push 的显式点，保留 TS 数组的重复项以便一致性检查能发现漂移。
    explicit = re.findall(r"key: '([^']+)'", text)
    for key in explicit:
        doc_type, _, action = key.partition(":")
        points.append(
            {
                "key": key,
                "labelZh": key,
                "labelEn": key,
                "module": "Identity",
                "kind": "field" if "." in doc_type else "action",
                "sensitive": True,
                "dataScopeRuleTypes": ["all"],
            }
        )
    # 这些权限使用常量拼入数组，不能由 key: 属性正则捕获。
    for key in (
        "accounts_payable:read",
        "expense_claim:approve_manager",
        "expense_claim:approve_finance",
    ):
        points.append(
            {
                "key": key,
                "labelZh": key,
                "labelEn": key,
                "module": "Accounts",
                "kind": "action",
                "sensitive": True,
                "dataScopeRuleTypes": ["all"],
            }
        )
    if target is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(points, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return points


def export_roles(source: Path = SOURCE, target: Path | None = ROLE_TARGET) -> dict[str, list[str]]:
    text = source.read_text(encoding="utf-8")
    start = text.index("const templatePermissions")
    end = text.index("const template =", start)
    block = text[start:end]
    result: dict[str, list[str]] = {}
    for match in re.finditer(r"(?m)^  ([a-z_]+): \[(.*?)\],?$", block, re.S):
        result[match.group(1)] = re.findall(r"'([^']+:[^']+)'", match.group(2))
    result["owner_manager"] = [str(item["key"]) for item in export(source, None)]
    if target is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def check(source: Path = SOURCE, target: Path = TARGET) -> None:
    expected = export(source, None)
    actual = json.loads(target.read_text(encoding="utf-8"))
    if actual != expected:
        raise SystemExit("permission_points.json 与前端 permissionCatalog 不一致")
    if len(actual) != 811:
        raise SystemExit(f"权限点数量异常：期望 811，实际 {len(actual)}")
    expected_roles = export_roles(source, None)
    actual_roles = json.loads(ROLE_TARGET.read_text(encoding="utf-8"))
    actual_permissions = {key: value for key, value in actual_roles.items() if key != "_dataScopes"}
    if actual_permissions != expected_roles:
        raise SystemExit("role_templates.json 与前端 roleTemplates 不一致")
    if "_dataScopes" not in actual_roles:
        raise SystemExit("role_templates.json 缺少 _dataScopes")


if __name__ == "__main__":
    if TARGET.exists() and ROLE_TARGET.exists():
        check()
    else:
        points = export()
        export_roles()
        if len(points) != 811:
            raise SystemExit(f"权限点数量异常：期望 811，实际 {len(points)}")
