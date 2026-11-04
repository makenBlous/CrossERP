"""审计记录导出为可离线验证的 zip。"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp import __version__
from crosserp.audit.chain import GENESIS_PREV_HASH
from crosserp.audit.log import append, payload_from_log
from crosserp.db.schema import AuditExport, AuditLog


def export_audit(
    session: Session,
    *,
    from_ts: datetime,
    to_ts: datetime,
    fmt: str,
    output: Path,
    requested_by: str,
) -> AuditExport:
    """导出时间范围内的审计记录，并记录导出动作。"""  # noqa: RUF002
    if fmt not in {"jsonl", "csv"}:
        raise ValueError("format 只能是 jsonl 或 csv")
    if output.exists():
        raise FileExistsError(f"输出文件已存在: {output}")
    rows = list(
        session.scalars(
            select(AuditLog)
            .where(AuditLog.ts >= from_ts, AuditLog.ts < to_ts)
            .order_by(AuditLog.seq)
        )
    )
    previous = rows[0].prev_hash if rows else _previous_hash(session, from_ts)
    records = [_record(row) for row in rows]
    data_name = "audit_log.jsonl" if fmt == "jsonl" else "audit_log.csv"
    data = _render(records, fmt)
    verify_md = _verify_instructions(data_name, fmt)
    files = {
        data_name: hashlib.sha256(data).hexdigest(),
        "VERIFY.md": hashlib.sha256(verify_md).hexdigest(),
    }
    manifest: dict[str, Any] = {
        "format_version": 1,
        "crosserp_version": __version__,
        "format": fmt,
        "data_file": data_name,
        "from_utc": from_ts.isoformat(),
        "to_utc": to_ts.isoformat(),
        "row_count": len(records),
        "first_seq": rows[0].seq if rows else None,
        "last_seq": rows[-1].seq if rows else None,
        "prev_hash_before_first": previous,
        "first_hash": rows[0].hash if rows else None,
        "last_hash": rows[-1].hash if rows else None,
        "files": files,
        "hash_algorithm": "sha256(prev_hash + canonical JSON payload)",
    }
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode(
        "utf-8"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(data_name, data)
        archive.writestr("manifest.json", manifest_bytes)
        archive.writestr("VERIFY.md", verify_md)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    export_row = AuditExport(
        id=uuid4(),
        requested_by=requested_by,
        from_ts=from_ts,
        to_ts=to_ts,
        format=fmt,
        row_count=len(rows),
        first_hash=rows[0].hash if rows else None,
        last_hash=rows[-1].hash if rows else None,
        file_sha256=digest,
        created_at=to_ts,
    )
    session.add(export_row)
    session.flush()
    append(
        session,
        "system",
        "audit.export",
        "audit_export",
        str(export_row.id),
        None,
        {"file": str(output), "row_count": len(rows), "sha256": digest},
        reason="审计包导出",
        self_approved=False,
        actor_name=requested_by,
    )
    return export_row


def _record(row: AuditLog) -> dict[str, Any]:
    payload = payload_from_log(row)
    payload["hash"] = row.hash
    return payload


def _render(rows: list[dict[str, Any]], fmt: str) -> bytes:
    if fmt == "jsonl":
        return (
            "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
            + ("\n" if rows else "")
        ).encode("utf-8")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=["seq", "hash", "payload_json"])
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "seq": row["seq"],
                "hash": row["hash"],
                "payload_json": json.dumps(
                    {k: v for k, v in row.items() if k != "hash"},
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def _previous_hash(session: Session, from_ts: datetime) -> str:
    row = session.scalar(
        select(AuditLog).where(AuditLog.ts < from_ts).order_by(AuditLog.seq.desc()).limit(1)
    )
    return GENESIS_PREV_HASH if row is None else row.hash


def _verify_instructions(data_name: str, fmt: str) -> bytes:
    return (
        "# 离线校验\n\n"
        f"本包的数据文件是 `{data_name}`（格式 `{fmt}`）。"  # noqa: RUF001
        "先确认 `manifest.json` 中 files 的 SHA-256，"  # noqa: RUF001
        "再从 prev_hash_before_first 开始按 hash_algorithm 逐行重算，"  # noqa: RUF001
        "最后比较 first_hash/last_hash。\n"
    ).encode()
