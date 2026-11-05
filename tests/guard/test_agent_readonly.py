import ast
from pathlib import Path


def test_agent_has_no_write_or_ledger_imports() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "crosserp" / "agent"
    forbidden = ("crosserp.ledger", "crosserp.approval.service", "crosserp.db.repo")
    violations: list[str] = []
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            names = [item.name for item in node.names] if isinstance(node, ast.Import) else []
            if module and any(module.startswith(item) for item in forbidden):
                violations.append(f"{path.name}: {module}")
            if any(any(name.startswith(item) for item in forbidden) for name in names):
                violations.append(f"{path.name}: import")
    assert violations == []
