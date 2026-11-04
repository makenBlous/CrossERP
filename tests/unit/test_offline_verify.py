"""离线审计包校验。"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from crosserp.audit.chain import GENESIS_PREV_HASH, compute_hash
from crosserp.audit.offline_verify import OfflineVerifyError, verify_export


def _package(path: Path, *, tamper: bool = False) -> None:
    payload = {
        "id": "1",
        "seq": 1,
        "prev_hash": GENESIS_PREV_HASH,
        "actor_type": "system",
        "actor_user_id": None,
        "actor_name": "system",
        "actor_role": None,
        "action": "import",
        "target_type": "batch",
        "target_id": "1",
        "before_json": None,
        "after_json": {"ok": True},
        "approval_id": None,
        "approver_id": None,
        "reason": None,
        "request_id": None,
        "ip": None,
        "user_agent": None,
        "self_approved": False,
        "hash_version": 2,
    }
    row_hash = compute_hash(GENESIS_PREV_HASH, payload)
    payload["hash"] = row_hash
    data = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode()
    verify = b"# verify\n"
    manifest = {
        "format_version": 1,
        "format": "jsonl",
        "data_file": "audit_log.jsonl",
        "row_count": 1,
        "prev_hash_before_first": GENESIS_PREV_HASH,
        "first_hash": row_hash,
        "last_hash": row_hash,
        "files": {
            "audit_log.jsonl": hashlib.sha256(data).hexdigest(),
            "VERIFY.md": hashlib.sha256(verify).hexdigest(),
        },
    }
    if tamper:
        data = data.replace(b"import", b"export")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("audit_log.jsonl", data)
        archive.writestr("VERIFY.md", verify)
        archive.writestr("manifest.json", json.dumps(manifest).encode())


def test_verify_export_and_tamper(tmp_path: Path) -> None:
    good = tmp_path / "good.zip"
    _package(good)
    verify_export(good)
    bad = tmp_path / "bad.zip"
    _package(bad, tamper=True)
    with pytest.raises(OfflineVerifyError, match="文件摘要不一致"):
        verify_export(bad)
