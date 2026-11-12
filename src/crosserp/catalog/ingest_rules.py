"""映射规则版本服务。"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.catalog.ingest import MappingRuleBody
from crosserp.db.schema import MappingRule
from crosserp.platform.principal import Principal


def save_mapping_rule_version(
    session: Session,
    rule_id: UUID,
    *,
    body: MappingRuleBody,
    principal: Principal,
) -> dict[str, Any]:
    """保存规则的新版本，并将旧版本标记为 superseded。"""  # noqa: RUF002
    current = session.get(MappingRule, rule_id)
    if current is None:
        raise not_found()
    if current.status != "active":
        raise APIError(ErrorCode.CONFLICT_VERSION, "映射规则版本已失效")

    now = datetime.now(UTC)
    next_version = _next_rule_version(session, current.rule_key)
    row = MappingRule(
        id=uuid4(),
        rule_key=current.rule_key,
        rule_version=next_version,
        kind=current.kind,
        body_json=body.model_dump(by_alias=True),
        status="active",
        verified=False,
        version=1,
        created_at=now,
        updated_at=now,
        created_by=principal.effective_user_id,
        on_behalf_of=principal.on_behalf_of,
    )
    current.status = "superseded"
    current.updated_at = now
    session.add(row)
    session.flush()
    return {
        "id": str(row.id),
        "ruleKey": row.rule_key,
        "kind": row.kind,
        "ruleVersion": row.rule_version,
        "version": row.version,
        "body": row.body_json,
        "status": row.status,
        "verified": row.verified,
        "previousId": str(current.id),
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def _next_rule_version(session: Session, rule_key: str) -> str:
    versions = session.scalars(
        select(MappingRule.rule_version).where(MappingRule.rule_key == rule_key)
    )
    numbers = [
        int(match.group(1)) for value in versions if (match := re.fullmatch(r"v(\d+)", value))
    ]
    return f"v{max(numbers, default=1) + 1}"


__all__ = ["save_mapping_rule_version"]
