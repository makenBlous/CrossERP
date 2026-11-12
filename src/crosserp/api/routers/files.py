"""FileObject JSON API。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile
from pydantic import Field
from sqlalchemy import select

from crosserp.api.errors import APIError, ErrorCode, not_found
from crosserp.api.metadata import api_endpoint
from crosserp.api.routers._platform_common import _dispatch_write, _principal_db, _write_guard
from crosserp.api.schemas import CamelModel
from crosserp.db.schema import FileObject
from crosserp.platform.dispatcher import RiskTier

router = APIRouter()

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


class FileUploadRequest(CamelModel):
    """上传表单中的可选 JSON 元数据。"""

    meta: str | None = Field(default=None)

    @classmethod
    def as_form(cls, meta: Annotated[str | None, Form()] = None) -> FileUploadRequest:
        return cls(meta=meta)


class FileRef(CamelModel):
    file_id: UUID = Field(alias="fileId")
    name: str
    size: int
    sha256: str
    content_type: str | None = Field(alias="contentType", default=None)


def _file_ref(row: FileObject) -> FileRef:
    return FileRef(
        fileId=row.id,
        name=row.filename,
        size=row.size,
        sha256=row.sha256,
        contentType=row.content_type,
    )


def _file_ref_payload(row: FileObject) -> dict[str, object]:
    return _file_ref(row).model_dump(mode="json", by_alias=True)


@router.post("/files", status_code=201, response_model=FileRef)
@api_endpoint(
    entity="FileObject", action="FileObject.create", permission="authenticated", risk_tier="low"
)
async def upload_file(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    _payload: Annotated[FileUploadRequest, Depends(FileUploadRequest.as_form)],
    csrf: str | None = Header(None, alias="X-CSRF-Token"),
) -> FileRef:
    principal, session = _principal_db(request)
    try:
        _write_guard(request, principal, csrf)
        filename = file.filename
        if filename is None:
            raise APIError(ErrorCode.VALIDATION_ERROR, "文件名不能为空", status_code=422)
        content = await file.read()
        size = len(content)
        if size == 0:
            raise APIError(ErrorCode.VALIDATION_ERROR, "文件不能为空", status_code=422)
        if size > MAX_FILE_SIZE_BYTES:
            raise APIError(ErrorCode.VALIDATION_ERROR, "文件超过大小限制", status_code=422)

        digest = hashlib.sha256(content).hexdigest()
        existing = session.scalar(select(FileObject).where(FileObject.sha256 == digest))
        if existing is not None:
            result = _dispatch_write(
                request,
                principal,
                session,
                permission="authenticated",
                risk=RiskTier.LOW,
                entity="FileObject",
                action="FileObject.create",
                work=lambda: _file_ref_payload(existing),
            )
            session.commit()
            return FileRef.model_validate(result)

        path = request.app.state.file_storage.write(digest, content)
        row = FileObject(
            id=uuid4(),
            sha256=digest,
            filename=filename,
            content_type=file.content_type,
            size=size,
            storage_path=str(path),
            uploaded_by=principal.user_id,
            created_at=datetime.now(UTC),
        )
        session.add(row)
        result = _dispatch_write(
            request,
            principal,
            session,
            permission="authenticated",
            risk=RiskTier.LOW,
            entity="FileObject",
            action="FileObject.create",
            work=lambda: _file_ref_payload(row),
        )
        session.commit()
        return FileRef.model_validate(result)
    finally:
        session.close()


@router.get("/files/{id}", response_model=FileRef)
@api_endpoint(
    entity="FileObject", action="FileObject.get", permission="authenticated", risk_tier="none"
)
def get_file(request: Request, id: UUID) -> FileRef:
    principal, session = _principal_db(request)
    try:
        row = session.get(FileObject, id)
        if row is None or row.uploaded_by != principal.effective_user_id:
            raise not_found()
        return _file_ref(row)
    finally:
        session.close()
