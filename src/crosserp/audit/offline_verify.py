"""不连接数据库验证审计导出包。只依赖 Python 标准库。"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

from crosserp.audit.chain import GENESIS_PREV_HASH, compute_hash


class OfflineVerifyError(ValueError):
    """导出包校验失败。"""


def verify_export(path: Path) -> None:
    """校验 zip 内文件摘要、记录数量和哈希链。"""
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            for required in ("manifest.json", "VERIFY.md"):
                if required not in names:
                    raise OfflineVerifyError(f"缺少 {required}")
            manifest = _json(archive.read("manifest.json"), "manifest.json")
            data_name = str(manifest.get("data_file", ""))
            if data_name not in names:
                raise OfflineVerifyError(f"缺少数据文件 {data_name}")
            files = manifest.get("files")
            if not isinstance(files, dict):
                raise OfflineVerifyError("manifest.files 格式错误")
            for name, expected in files.items():
                if name not in names:
                    raise OfflineVerifyError(f"manifest 指向不存在的文件 {name}")
                actual = hashlib.sha256(archive.read(name)).hexdigest()
                if actual != expected:
                    raise OfflineVerifyError(f"文件摘要不一致: {name}")
            rows = _read_rows(archive.read(data_name), str(manifest.get("format")))
            _verify_rows(rows, manifest)
    except zipfile.BadZipFile as exc:
        raise OfflineVerifyError(f"不是有效 zip: {exc}") from exc


def _json(raw: bytes, name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OfflineVerifyError(f"{name} 不是有效 JSON") from exc
    if not isinstance(value, dict):
        raise OfflineVerifyError(f"{name} 必须是对象")
    return value


def _read_rows(raw: bytes, fmt: str) -> list[dict[str, Any]]:
    if fmt == "jsonl":
        rows: list[dict[str, Any]] = []
        for line_no, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
            if not line:
                continue
            rows.append(_json(line.encode("utf-8"), f"数据第 {line_no} 行"))
        return rows
    if fmt == "csv":
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for item in reader:
            payload_raw = item.get("payload_json")
            if payload_raw is None:
                raise OfflineVerifyError("CSV 缺少 payload_json")
            payload = _json(payload_raw.encode("utf-8"), "CSV payload_json")
            payload["hash"] = item.get("hash")
            rows.append(payload)
        return rows
    raise OfflineVerifyError(f"不支持的格式 {fmt}")


def _verify_rows(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    expected_count = manifest.get("row_count")
    if expected_count != len(rows):
        raise OfflineVerifyError(f"条数不一致: manifest={expected_count}, actual={len(rows)}")
    previous = str(manifest.get("prev_hash_before_first", GENESIS_PREV_HASH))
    first_hash: str | None = None
    last_hash: str | None = None
    for index, row in enumerate(rows, start=1):
        row_hash = row.pop("hash", None)
        if not isinstance(row_hash, str):
            raise OfflineVerifyError(f"第 {index} 行缺少 hash")
        if row.get("prev_hash") != previous:
            raise OfflineVerifyError(f"第 {index} 行 prev_hash 不连续")
        expected = compute_hash(previous, row)
        if row_hash != expected:
            raise OfflineVerifyError(f"第 {index} 行 hash 不一致")
        first_hash = row_hash if first_hash is None else first_hash
        last_hash = row_hash
        previous = row_hash
    if manifest.get("first_hash") != first_hash or manifest.get("last_hash") != last_hash:
        raise OfflineVerifyError("manifest 首尾 hash 不一致")
