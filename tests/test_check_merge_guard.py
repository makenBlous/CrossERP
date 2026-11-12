"""合并前检查脚本的样例：每条规则至少一个命中和一个不命中。"""

# 样例说明沿用项目中文口径。
# ruff: noqa: RUF002

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "check_merge_guard.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_merge_guard", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout


def _init(repo: Path) -> None:
    _git(repo, "init")
    _git(repo, "config", "user.email", "merge-guard@example.com")
    _git(repo, "config", "user.name", "merge-guard")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.autocrlf", "false")


def _write(repo: Path, relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )


def _rule_lines(output: str, rule_id: str) -> list[str]:
    return [
        line
        for line in output.splitlines()
        if line.startswith(f"{rule_id}  ") or line.startswith(f"豁免 {rule_id}  ")
    ]


def test_list_rules_exports_every_rule_id() -> None:
    module = _load()
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--list-rules"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    assert completed.returncode == 0
    for rule_id, _description in module.RULES:
        assert rule_id in completed.stdout


def test_shared_module_constants_match_repository_files() -> None:
    module = _load()
    for relative in (
        module.SCOPE_MODULE,
        module.METADATA_MODULE,
        module.IDEMPOTENCY_MIDDLEWARE,
        module.FACTORY_MODULE,
        module.APPROVAL_MODULE,
        module.AUDIT_MODULE,
    ):
        assert (REPO / relative).is_file()


def test_missing_base_raises() -> None:
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.run(
            [sys.executable, str(SCRIPT)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )


def test_invalid_git_revision_raises(tmp_path: Path) -> None:
    _init(tmp_path)
    _write(tmp_path, "src/app.py", "x = 1\n")
    _commit(tmp_path, "base")
    completed = _run(tmp_path, "--base", "not-a-rev")
    assert completed.returncode != 0
    assert "Traceback" in completed.stderr


def test_no_hits_exits_zero(tmp_path: Path) -> None:
    _init(tmp_path)
    _write(tmp_path, "src/app.py", "def ready() -> int:\n    return 1\n")
    base = _commit(tmp_path, "base")
    _write(tmp_path, "src/app.py", "def ready() -> int:\n    return 2\n")
    head = _commit(tmp_path, "head")
    completed = _run(tmp_path, "--base", base, "--head", head)
    assert completed.returncode == 0
    assert completed.stdout.strip() == ""


def test_g1_flags_security_assertion_deletion_not_pure_move(tmp_path: Path) -> None:
    _init(tmp_path)
    _write(
        tmp_path,
        "tests/test_sec.py",
        "def test_denied() -> None:\n    assert response.status_code == 403\n",
    )
    base = _commit(tmp_path, "base")
    _write(tmp_path, "tests/test_sec.py", "def test_denied() -> None:\n    assert True\n")
    head = _commit(tmp_path, "relaxed")
    hit = _run(tmp_path, "--base", base, "--head", head)
    assert hit.returncode == 1
    assert _rule_lines(hit.stdout, "G1")

    _write(
        tmp_path,
        "tests/test_sec.py",
        "def test_denied() -> None:\n        assert response.status_code == 403\n",
    )
    moved = _commit(tmp_path, "moved")
    pure_move = _run(tmp_path, "--base", head, "--head", moved)
    assert pure_move.returncode == 0
    assert _rule_lines(pure_move.stdout, "G1") == []


def test_g1_flags_status_and_operator_relaxation(tmp_path: Path) -> None:
    _init(tmp_path)
    _write(
        tmp_path,
        "tests/test_status.py",
        "def test_status() -> None:\n"
        "    assert response.status_code == 403\n"
        "    assert body == {'ok': False}\n",
    )
    base = _commit(tmp_path, "base")
    _write(
        tmp_path,
        "tests/test_status.py",
        "def test_status() -> None:\n"
        "    assert response.status_code == 200\n"
        "    assert body in ({'ok': False}, {'ok': True})\n",
    )
    head = _commit(tmp_path, "relaxed")
    completed = _run(tmp_path, "--base", base, "--head", head)
    assert completed.returncode == 1
    assert len(_rule_lines(completed.stdout, "G1")) >= 2


def test_g1_flags_deleted_test_file_and_intra_range_medium_risk_relaxation(
    tmp_path: Path,
) -> None:
    _init(tmp_path)
    _write(tmp_path, "README.md", "base\n")
    base = _commit(tmp_path, "base")
    _write(
        tmp_path,
        "tests/test_medium.py",
        "def test_medium_action_requires_entity_identity_for_undo() -> None:\n"
        "    with pytest.raises(APIError) as error:\n"
        "        dispatch()\n"
        "    assert error.value.code is ErrorCode.VALIDATION_FAILED\n",
    )
    _commit(tmp_path, "strict")
    _write(
        tmp_path,
        "tests/test_medium.py",
        "def test_medium_action_requires_entity_identity_for_undo() -> None:\n"
        "    dispatch()\n"
        "    assert session.scalar(select(AgentUndo)) is None\n",
    )
    head = _commit(tmp_path, "relaxed")
    completed = _run(tmp_path, "--base", base, "--head", head)
    assert completed.returncode == 1
    g1 = _rule_lines(completed.stdout, "G1")
    assert any("pytest.raises" in line for line in g1)
    assert any("VALIDATION_FAILED" in line for line in g1)

    _git(tmp_path, "rm", "tests/test_medium.py")
    deleted = _commit(tmp_path, "deleted")
    file_gone = _run(tmp_path, "--base", head, "--head", deleted)
    assert file_gone.returncode == 1
    assert any("整文件删除" in line for line in _rule_lines(file_gone.stdout, "G1"))


def test_g1_ignores_non_weakening_assertion_rewrite(tmp_path: Path) -> None:
    _init(tmp_path)
    _write(
        tmp_path,
        "tests/test_rewrite.py",
        "def test_denied() -> None:\n    assert denied.value.code is ErrorCode.NOT_FOUND\n",
    )
    base = _commit(tmp_path, "base")
    _write(
        tmp_path,
        "tests/test_rewrite.py",
        "def test_denied() -> None:\n    assert denied.value.code is ErrorCode.FORBIDDEN\n",
    )
    head = _commit(tmp_path, "rewrite")
    completed = _run(tmp_path, "--base", base, "--head", head)
    assert completed.returncode == 0
    assert _rule_lines(completed.stdout, "G1") == []


def test_g2_flags_new_skip_and_raised_timeout_only(tmp_path: Path) -> None:
    _init(tmp_path)
    _write(
        tmp_path,
        "tests/test_slow.py",
        "import pytest\n\n@pytest.mark.timeout(5)\ndef test_slow() -> None:\n    assert True\n",
    )
    base = _commit(tmp_path, "base")
    _write(
        tmp_path,
        "tests/test_slow.py",
        "import pytest\n\n"
        "@pytest.mark.skip\n"
        "@pytest.mark.skipif(True, reason='later')\n"
        "@pytest.mark.xfail\n"
        "@pytest.mark.timeout(30)\n"
        "def test_slow() -> None:\n"
        "    pytest.skip('no')\n"
        "    pytest.importorskip('missing')\n",
    )
    head = _commit(tmp_path, "skipped")
    completed = _run(tmp_path, "--base", base, "--head", head)
    assert completed.returncode == 1
    g2 = "\n".join(_rule_lines(completed.stdout, "G2"))
    assert "pytest.mark.skip" in g2
    assert "skipif" in g2
    assert "xfail" in g2
    assert "pytest.skip" in g2
    assert "importorskip" in g2
    assert "timeout" in g2

    _write(
        tmp_path,
        "tests/test_slow.py",
        "import pytest\n\n# pytest.mark.skip is a comment\n"
        "@pytest.mark.timeout(1)\n"
        "def test_slow() -> None:\n    assert True\n",
    )
    comment = _commit(tmp_path, "comment")
    quiet = _run(tmp_path, "--base", head, "--head", comment)
    assert _rule_lines(quiet.stdout, "G2") == []


def test_d1_flags_default_fallbacks_not_orm_get(tmp_path: Path) -> None:
    _init(tmp_path)
    _write(tmp_path, "src/app.py", "def ready() -> int:\n    return 1\n")
    base = _commit(tmp_path, "base")
    _write(
        tmp_path,
        "src/app.py",
        "def read(payload, session, model, key, value, obj):\n"
        "    kept = payload.get('name')\n"
        "    row = session.get(model, key)\n"
        "    fallback = payload.get('name', {})\n"
        "    hidden = getattr(obj, 'legacy', None)\n"
        "    data = value or {}\n"
        "    items = value or []\n"
        "    label = value or ''\n"
        "    return kept, row, fallback, hidden, data, items, label\n",
    )
    head = _commit(tmp_path, "fallback")
    completed = _run(tmp_path, "--base", base, "--head", head)
    assert completed.returncode == 1
    d1 = "\n".join(_rule_lines(completed.stdout, "D1"))
    assert "payload.get('name', {})" in d1
    assert "getattr" in d1
    assert "or {}" in d1
    assert "or []" in d1
    assert "or ''" in d1
    assert "session.get" not in d1
    assert "payload.get('name')" not in d1


def test_d2_flags_swallowed_errors_and_silent_returns(tmp_path: Path) -> None:
    _init(tmp_path)
    _write(tmp_path, "src/app.py", "def ready() -> int:\n    return 1\n")
    base = _commit(tmp_path, "base")
    _write(
        tmp_path,
        "src/app.py",
        "import contextlib\n\n"
        "def swallow(value, log):\n"
        "    try:\n"
        "        work()\n"
        "    except Exception:\n"
        "        return None\n"
        "    try:\n"
        "        work()\n"
        "    except ValueError:\n"
        "        pass\n"
        "    with contextlib.suppress(KeyError):\n"
        "        work()\n"
        "    if value is None:\n"
        "        return\n"
        "    if not value:\n"
        "        return\n"
        "\n"
        "def strict(value):\n"
        "    try:\n"
        "        work()\n"
        "    except Exception as exc:\n"
        "        raise RuntimeError('failed') from exc\n"
        "    if value is None:\n"
        "        raise RuntimeError('missing')\n",
    )
    head = _commit(tmp_path, "swallow")
    completed = _run(tmp_path, "--base", base, "--head", head)
    assert completed.returncode == 1
    d2 = "\n".join(_rule_lines(completed.stdout, "D2"))
    assert "except Exception" in d2
    assert "except ValueError" in d2
    assert "suppress" in d2
    assert "value is None" in d2
    assert "if not value" in d2
    assert "raise RuntimeError('failed')" not in d2
    assert "raise RuntimeError('missing')" not in d2


def test_d3_flags_optional_switches_not_scope_dispatch(tmp_path: Path) -> None:
    _init(tmp_path)
    _write(tmp_path, "src/app.py", "def ready(value: int) -> int:\n    return value\n")
    base = _commit(tmp_path, "base")
    _write(
        tmp_path,
        "src/app.py",
        "def ready(value: int, maybe: int | None = None) -> int:\n"
        "    if hasattr(value, 'legacy'):\n"
        "        return 0\n"
        "    before = before if isinstance(before, dict) else {}\n"
        "    if isinstance(scope, AllStores):\n"
        "        return value\n"
        "    return maybe or value\n",
    )
    _write(
        tmp_path,
        "src/crosserp/db/migrations/versions/0099_demo.py",
        "branch_labels: str | None = None\ndepends_on: str | None = None\n",
    )
    head = _commit(tmp_path, "optional")
    completed = _run(tmp_path, "--base", base, "--head", head)
    assert completed.returncode == 1
    d3 = "\n".join(_rule_lines(completed.stdout, "D3"))
    assert "int | None = None" in d3
    assert "hasattr" in d3
    assert "isinstance(before, dict)" in d3
    assert "AllStores" not in d3
    assert "branch_labels" not in d3


def test_s1_flags_hand_rolled_store_scope_outside_shared_module(tmp_path: Path) -> None:
    module = _load()
    _init(tmp_path)
    _write(tmp_path, "src/app.py", "def ready() -> int:\n    return 1\n")
    base = _commit(tmp_path, "base")
    _write(
        tmp_path,
        "src/orders.py",
        "def listed(rows):\n"
        "    store_ids = set()\n"
        "    for row in rows:\n"
        "        store_ids.add(row.store_id)\n"
        "    return select(Order).where(Order.store_id.in_(store_ids))\n",
    )
    _write(
        tmp_path,
        "src/shared_scope.py",
        "from crosserp.iam.scope import apply_store_scope\n\n"
        "def listed(statement, column, scope, store_ids):\n"
        "    store_ids = set(store_ids)\n"
        "    return apply_store_scope(statement, column, scope)\n",
    )
    _write(
        tmp_path,
        module.SCOPE_MODULE,
        "def resolve_store_scope(store_ids):\n"
        "    store_ids = set(store_ids)\n"
        "    return store_ids\n",
    )
    head = _commit(tmp_path, "scope")
    completed = _run(tmp_path, "--base", base, "--head", head)
    assert completed.returncode == 1
    s1 = "\n".join(_rule_lines(completed.stdout, "S1"))
    assert "src/orders.py" in s1
    assert "src/shared_scope.py" not in s1
    assert module.SCOPE_MODULE not in s1


def test_s2_flags_custom_idempotency_not_shared_forwarding(tmp_path: Path) -> None:
    module = _load()
    _init(tmp_path)
    _write(tmp_path, "src/app.py", "def ready() -> int:\n    return 1\n")
    base = _commit(tmp_path, "base")
    _write(
        tmp_path,
        "src/custom_idem.py",
        "def replay(request, cache):\n"
        "    key = request.headers['Idempotency-Key']\n"
        "    return cache._replay(key)\n"
        "\n"
        "def own(scope, body):\n"
        "    return IdempotencyKey(scope=scope, body=body)\n",
    )
    _write(
        tmp_path,
        "src/forward.py",
        "def post(request, idempotency_key=None):\n"
        "    return dispatch(idempotency_key=request.headers.get('Idempotency-Key'))\n",
    )
    _write(
        tmp_path,
        module.IDEMPOTENCY_MIDDLEWARE,
        "def record(request):\n    return request.headers.get('Idempotency-Key')\n",
    )
    _write(
        tmp_path,
        module.METADATA_MODULE,
        "def api_endpoint(idempotency):\n    return idempotency\n",
    )
    head = _commit(tmp_path, "idem")
    completed = _run(tmp_path, "--base", base, "--head", head)
    assert completed.returncode == 1
    s2 = "\n".join(_rule_lines(completed.stdout, "S2"))
    assert "src/custom_idem.py" in s2
    assert "src/forward.py" not in s2
    assert module.IDEMPOTENCY_MIDDLEWARE not in s2
    assert module.METADATA_MODULE not in s2


def test_s3_flags_private_dispatcher_approval_shell_and_audit_write(tmp_path: Path) -> None:
    module = _load()
    _init(tmp_path)
    _write(tmp_path, "src/app.py", "def ready() -> int:\n    return 1\n")
    base = _commit(tmp_path, "base")
    _write(
        tmp_path,
        "src/custom_exec.py",
        "def run(session):\n"
        "    dispatcher = ActionDispatcher(session=session)\n"
        "    shell = _ApprovalCompat({'state': 'awaiting'})\n"
        "    session.add(AuditLog(action='write'))\n"
        "    return dispatcher, shell\n",
    )
    _write(
        tmp_path,
        module.FACTORY_MODULE,
        "def make_action_dispatcher(session):\n    return ActionDispatcher(session=session)\n",
    )
    _write(
        tmp_path,
        module.AUDIT_MODULE,
        "def record():\n    return AuditLog(action='shared')\n",
    )
    head = _commit(tmp_path, "shell")
    completed = _run(tmp_path, "--base", base, "--head", head)
    assert completed.returncode == 1
    s3 = "\n".join(_rule_lines(completed.stdout, "S3"))
    assert "ActionDispatcher" in s3
    assert "_ApprovalCompat" in s3
    assert "AuditLog" in s3
    assert module.FACTORY_MODULE not in s3
    assert module.AUDIT_MODULE not in s3


def test_waiver_requires_reason_and_suppresses_matching_hit(tmp_path: Path) -> None:
    _init(tmp_path)
    _write(
        tmp_path,
        "tests/test_sec.py",
        "def test_denied() -> None:\n    assert response.status_code == 403\n",
    )
    base = _commit(tmp_path, "base")
    _write(tmp_path, "tests/test_sec.py", "def test_denied() -> None:\n    assert True\n")
    head = _commit(tmp_path, "relaxed")
    first = _run(tmp_path, "--base", base, "--head", head)
    assert first.returncode == 1
    fingerprint = first.stdout.split()[-1]
    assert len(fingerprint) == 12

    waiver = tmp_path / "waivers.txt"
    waiver.write_text(f"{fingerprint}\t太短\n", encoding="utf-8")
    short = _run(tmp_path, "--base", base, "--head", head, "--waivers", str(waiver))
    assert short.returncode == 2

    waiver.write_text(f"{fingerprint}\t验收报告确认这处改写仍保持拒绝语义\n", encoding="utf-8")
    waived = _run(tmp_path, "--base", base, "--head", head, "--waivers", str(waiver))
    assert waived.returncode == 0
    assert "豁免 G1" in waived.stdout
    assert "验收报告确认这处改写仍保持拒绝语义" in waived.stdout


def test_head_omitted_includes_uncommitted_worktree(tmp_path: Path) -> None:
    _init(tmp_path)
    _write(tmp_path, "src/app.py", "def ready() -> int:\n    return 1\n")
    base = _commit(tmp_path, "base")
    _write(tmp_path, "src/app.py", "def ready(payload):\n    return payload.get('name', {})\n")
    dirty = _run(tmp_path, "--base", base)
    assert dirty.returncode == 1
    assert _rule_lines(dirty.stdout, "D1")
    clean = _run(tmp_path, "--base", base, "--head", "HEAD")
    assert clean.returncode == 0
