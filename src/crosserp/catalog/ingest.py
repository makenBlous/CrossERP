"""导入批次的落地与清洗核心服务。

本模块只负责原件落地、确定性清洗和计数；投射由后续功能接管。
"""

# ruff: noqa: RUF002

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.db.schema import CleansingIssue, FileObject, ImportBatch, MappingRule, RawRow


class MappingRuleBody(BaseModel):
    """清洗链路支持的映射规则体。"""

    model_config = ConfigDict(extra="forbid")

    columns: dict[StrictStr, StrictStr] = Field(default_factory=dict)
    required: list[StrictStr] = Field(default_factory=list)
    amountFields: list[StrictStr] = Field(default_factory=list)
    periodField: StrictStr | None = None
    directionField: StrictStr | None = None


def _parse_mapping_rule_body(body: Any) -> MappingRuleBody:
    try:
        return MappingRuleBody.model_validate(body)
    except ValidationError as exc:
        raise APIError(
            ErrorCode.VALIDATION_ERROR,
            "映射规则格式无效",
            details={"errors": exc.errors()},
        ) from exc


def land_file(
    session: Session,
    file_id: UUID,
    *,
    kind: str,
    mapping_rule_version: str,
    created_by: UUID,
    source: str = "file",
    on_behalf_of: UUID | None = None,
) -> ImportBatch:
    """把 FileObject 原样落地为批次和 RawRow；同一 sha256 返回原批次。"""
    file = session.get(FileObject, file_id)
    if file is None:
        raise not_found(message="原件不存在")
    rule = session.scalar(
        select(MappingRule).where(MappingRule.rule_version == mapping_rule_version)
    )
    if rule is None:
        raise APIError(ErrorCode.UNVERIFIED_RULE_VERSION, "映射规则版本不存在")
    existing = session.scalar(select(ImportBatch).where(ImportBatch.file_sha256 == file.sha256))
    if existing is not None:
        return existing

    now = datetime.now(UTC)
    batch = ImportBatch(
        id=uuid4(),
        connector_id=rule.rule_key,
        connector_version=rule.rule_version,
        file_name=file.filename,
        file_sha256=file.sha256,
        imported_at=now,
        row_count=0,
        status="uploaded",
        error_count=0,
        source=source,
        kind=kind,
        mapping_rule_version=rule.rule_version,
        counts_json={},
        created_by=created_by,
        on_behalf_of=on_behalf_of,
        received_at=now,
    )
    session.add(batch)
    session.flush()
    rows = list(_read_file(Path(file.storage_path), file.content_type))
    for row_no, payload in rows:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        session.add(
            RawRow(
                batch_id=batch.id,
                row_no=row_no,
                payload_json=payload,
                sha256=hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
                received_at=now,
            )
        )
    batch.row_count = len(rows)
    batch.landed_count = len(rows)
    batch.counts_json = {
        "landed": len(rows),
        "valid": 0,
        "duplicate": 0,
        "quarantined": 0,
        "projected": 0,
    }
    batch.status = "landed"
    return batch


def register_mapping_rule(
    session: Session,
    *,
    rule_key: str,
    rule_version: str,
    kind: str,
    body: dict[str, Any],
    verified: bool = False,
) -> MappingRule:
    """登记一个不可覆盖的规则版本；更新规则只会新增版本。"""
    parsed_body = _parse_mapping_rule_body(body)
    existing = session.scalar(
        select(MappingRule).where(
            MappingRule.rule_key == rule_key, MappingRule.rule_version == rule_version
        )
    )
    if existing is not None:
        return existing
    rule = MappingRule(
        id=uuid4(),
        rule_key=rule_key,
        rule_version=rule_version,
        kind=kind,
        body_json=parsed_body.model_dump(),
        status="active",
        verified=verified,
        created_at=datetime.now(UTC),
    )
    session.add(rule)
    session.flush()
    return rule


def ingest_file(
    session: Session,
    path: Path,
    *,
    uploaded_by: UUID,
    kind: str,
    mapping_rule_version: str,
    content_type: str | None = None,
) -> ImportBatch:
    """文件导入入口：登记 FileObject 后执行落地和清洗。"""
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    file = session.scalar(select(FileObject).where(FileObject.sha256 == digest))
    if file is None:
        file = FileObject(
            id=uuid4(),
            sha256=digest,
            filename=path.name,
            content_type=content_type,
            size=len(content),
            storage_path=str(path),
            uploaded_by=uploaded_by,
            created_at=datetime.now(UTC),
        )
        session.add(file)
        session.flush()
    batch = land_file(
        session,
        file.id,
        kind=kind,
        mapping_rule_version=mapping_rule_version,
        created_by=uploaded_by,
    )
    if batch.status == "landed":
        return cleanse_batch(session, batch.id)
    return batch


def cleanse_batch(session: Session, batch_id: UUID) -> ImportBatch:
    """按批次绑定的映射规则确定性清洗，问题行进入隔离区。"""
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise not_found(message="导入批次不存在")
    if batch.status == "cleansed":
        return batch
    if batch.status != "landed":
        raise APIError(ErrorCode.ILLEGAL_TRANSITION, "只有已落地批次可以清洗")
    rule = session.scalar(
        select(MappingRule).where(MappingRule.rule_version == batch.mapping_rule_version)
    )
    if rule is None:
        raise APIError(ErrorCode.UNVERIFIED_RULE_VERSION, "批次绑定的映射规则不存在")
    rule_body = _parse_mapping_rule_body(rule.body_json)
    required = list(rule_body.required)
    amount_fields = set(rule_body.amountFields)
    period_field = rule_body.periodField
    direction_field = rule_body.directionField
    valid = quarantined = duplicate = 0
    seen: set[str] = set()
    rows = list(
        session.scalars(select(RawRow).where(RawRow.batch_id == batch.id).order_by(RawRow.row_no))
    )
    for raw in rows:
        issue: tuple[str, str | None, str, dict[str, Any]] | None
        if not isinstance(raw.payload_json, dict):
            issue = ("invalid", None, "原始记录必须是对象", {})
            fingerprint = None
        else:
            payload = _normalise_payload(raw.payload_json, rule_body.columns)
            fingerprint = json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            issue = None
            for field in required:
                if not str(payload.get(field, "")).strip():
                    issue = ("invalid", field, "必填项为空", {})
                    break
            if issue is None:
                for field in amount_fields:
                    value = str(payload.get(field, "")).strip()
                    try:
                        amount = Decimal(value)
                    except InvalidOperation:
                        issue = ("invalid", field, "金额无法解析", {})
                        break
                    exponent = amount.as_tuple().exponent
                    if not amount.is_finite() or not isinstance(exponent, int) or exponent < -4:
                        issue = ("invalid", field, "金额精度超过万分位", {})
                        break
            if issue is None and period_field:
                value = str(payload.get(period_field, "")).strip()
                if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
                    issue = ("invalid", period_field, "期间必须是 YYYY-MM", {})
            if issue is None and direction_field:
                value = str(payload.get(direction_field, "")).strip().casefold()
                if value not in {"借", "贷", "借方", "贷方", "debit", "credit"}:
                    issue = ("invalid", direction_field, "借贷方向无效", {})
            if issue is None and fingerprint in seen:
                issue = (
                    "duplicate",
                    None,
                    "批次内原始记录重复",
                    {"fingerprint": hashlib.sha256(fingerprint.encode()).hexdigest()},
                )
        if issue is None:
            assert fingerprint is not None
            seen.add(fingerprint)
            valid += 1
            continue
        issue_kind, issue_field, message, suggestion = issue
        if issue_kind == "duplicate":
            duplicate += 1
        quarantined += 1
        session.add(
            CleansingIssue(
                id=uuid4(),
                batch_id=batch.id,
                raw_record_id=raw.id,
                row_no=raw.row_no,
                kind=issue_kind,
                field=issue_field,
                message=message,
                suggestion_json=suggestion,
                status="open",
                created_at=datetime.now(UTC),
            )
        )
    batch.valid_count = valid
    batch.duplicate_count = duplicate
    batch.quarantined_count = quarantined
    batch.counts_json = {
        "landed": batch.landed_count,
        "valid": valid,
        "duplicate": duplicate,
        "quarantined": quarantined,
        "projected": batch.projected_count,
    }
    batch.status = "cleansed"
    return batch


def _read_file(path: Path, content_type: str | None) -> list[tuple[int, Any]]:
    if content_type == "application/json" or path.suffix.casefold() == ".json":
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(value, list):
            raise APIError(ErrorCode.VALIDATION_ERROR, "JSON 原件必须是对象数组")
        return list(enumerate(value, 1))
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [(index, dict(row)) for index, row in enumerate(csv.DictReader(handle), 2)]


def _normalise_payload(payload: dict[str, Any], columns: dict[str, str]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in payload.items():
        canonical = next(
            (target for target, source_name in columns.items() if source_name == key), str(key)
        )
        text = unicodedata.normalize("NFKC", str(value)).strip() if value is not None else ""
        output[canonical] = text
    return output


__all__ = ["cleanse_batch", "ingest_file", "land_file", "register_mapping_rule"]
