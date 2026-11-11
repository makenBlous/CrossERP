"""FileObject API 验收。"""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crosserp.auth.roles import Role
from crosserp.db.repo.users import create_user
from crosserp.db.schema import AppUser, FileObject


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return str(client.cookies["crosserp_csrf"])


def _create_user(api_engine, username: str) -> None:
    with Session(api_engine) as session, session.begin():
        create_user(session, username=username, password="password-123", roles=(Role.OPERATOR,))


def _upload(client: TestClient, csrf: str, content: bytes, *, key: str | None = None):
    headers = {"X-CSRF-Token": csrf}
    if key is not None:
        headers["Idempotency-Key"] = key
    return client.post(
        "/api/v1/files",
        files={"file": ("report.csv", content, "text/csv")},
        headers=headers,
    )


def test_upload_returns_file_ref_and_records_uploader(
    json_client: TestClient, api_engine, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CROSSERP_FILES_DIR", str(tmp_path))
    _create_user(api_engine, "file-owner")
    csrf = _login(json_client, "file-owner", "password-123")

    response = _upload(json_client, csrf, b"a,b\n1,2\n")

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"fileId", "name", "size", "sha256", "contentType"}
    assert body["sha256"] == hashlib.sha256(b"a,b\n1,2\n").hexdigest()
    assert body["size"] == 8
    assert body["contentType"] == "text/csv"
    with Session(api_engine) as session:
        row = session.get(FileObject, UUID(body["fileId"]))
        assert row is not None
        assert row.uploaded_by == session.scalar(
            select(AppUser.id).where(AppUser.username == "file-owner")
        )
        assert Path(row.storage_path).parent == tmp_path


def test_upload_deduplicates_without_second_file(
    json_client: TestClient, api_engine, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CROSSERP_FILES_DIR", str(tmp_path))
    _create_user(api_engine, "file-dedup")
    csrf = _login(json_client, "file-dedup", "password-123")

    first = _upload(json_client, csrf, b"same")
    second = _upload(json_client, csrf, b"same")

    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert len([path for path in tmp_path.iterdir() if path.name != "api.db"]) == 1
    with Session(api_engine) as session:
        assert session.scalar(select(func.count()).select_from(FileObject)) == 1


def test_upload_idempotency_replays_without_second_write(
    json_client: TestClient, api_engine, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CROSSERP_FILES_DIR", str(tmp_path))
    _create_user(api_engine, "file-idempotent")
    csrf = _login(json_client, "file-idempotent", "password-123")

    first = _upload(json_client, csrf, b"once", key="file-once")
    replay = _upload(json_client, csrf, b"once", key="file-once")

    assert first.status_code == 201
    assert replay.status_code == 409
    with Session(api_engine) as session:
        assert session.scalar(select(func.count()).select_from(FileObject)) == 1
    with Session(api_engine) as session:
        assert session.scalar(select(func.count()).select_from(FileObject)) == 1


def test_file_metadata_hides_storage_path_and_forbids_other_user(
    json_client: TestClient, api_engine, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CROSSERP_FILES_DIR", str(tmp_path))
    _create_user(api_engine, "file-visible")
    _create_user(api_engine, "file-hidden")
    csrf = _login(json_client, "file-visible", "password-123")
    uploaded = _upload(json_client, csrf, b"private")
    file_id = uploaded.json()["fileId"]

    metadata = json_client.get(f"/api/v1/files/{file_id}")
    assert metadata.status_code == 200
    assert "storagePath" not in metadata.json()
    assert "storage_path" not in metadata.json()

    csrf = _login(json_client, "file-hidden", "password-123")
    assert json_client.get(f"/api/v1/files/{file_id}").status_code == 404
    assert json_client.get("/api/v1/files/00000000-0000-0000-0000-000000000000").status_code == 404


def test_empty_file_is_validation_error(
    json_client: TestClient, api_engine, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CROSSERP_FILES_DIR", str(tmp_path))
    _create_user(api_engine, "file-empty")
    csrf = _login(json_client, "file-empty", "password-123")

    response = _upload(json_client, csrf, b"")

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_oversized_file_is_validation_error(
    json_client: TestClient, api_engine, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CROSSERP_FILES_DIR", str(tmp_path))
    _create_user(api_engine, "file-large")
    csrf = _login(json_client, "file-large", "password-123")

    response = _upload(json_client, csrf, b"x" * (10 * 1024 * 1024 + 1))

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
