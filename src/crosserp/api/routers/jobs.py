"""后台任务查询接口。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import Field

from crosserp.api.errors import not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers.platform import _principal_db
from crosserp.api.schemas import CamelModel
from crosserp.db.schema import Job

router = APIRouter()


class JobResponse(CamelModel):
    id: UUID
    kind: str
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    progress: Decimal = Field(ge=0, le=1)
    error: str | None = None
    result_ref: str | None = None
    created_by: UUID
    created_at: datetime


@router.get("/jobs/{id}", response_model=JobResponse)
@api_endpoint(entity="Job", action="Job.get", permission="authenticated", risk_tier="none")
def get_job(request: Request, id: UUID) -> JobResponse:
    principal, session = _principal_db(request)
    try:
        row = session.get(Job, id)
        if row is None or row.created_by != principal.effective_user_id:
            raise not_found()
        return JobResponse(
            id=row.id,
            kind=row.kind,
            status=cast(
                Literal["queued", "running", "succeeded", "failed", "cancelled"], row.status
            ),
            progress=row.progress,
            error=row.error,
            result_ref=row.result_ref,
            created_by=row.created_by,
            created_at=row.created_at,
        )
    finally:
        session.close()


__all__ = ["router"]
