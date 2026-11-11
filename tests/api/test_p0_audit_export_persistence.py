"""审计导出包落库与完整性验收。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crosserp.db.schema import AppUser, AuditExport, AuditLog, FileObject, SecurityEvent
from crosserp.platform.principal import ActorType, Principal, get_principal


def _principal(user_id=None, role: str = "auditor", *, agent: bool = False) -> Principal:
    effective_id = user_id or uuid4()
    return Principal(
        user_id=effective_id,
        roles=frozenset({role}),
        actor_type=ActorType.AGENT if agent else ActorType.HUMAN,
        agent_id="audit-agent" if agent else None,
        on_behalf_of=effective_id if agent else None,
        channel="mcp" if agent else "web",
    )


def _bind_principal(client: TestClient, principal: Principal) -> None:
    with Session(client.app.state.database_engine) as session, session.begin():
        from crosserp.db.repo.users import grant_role

        if session.get(AppUser, principal.user_id) is None:
            session.add(
                AppUser(
                    id=principal.user_id,
                    username=f"export-{principal.user_id.hex[:12]}",
                    display_name="导出测试身份",
                    password_hash="x",
                    is_active=True,
                    failed_logins=0,
                    locked_until=None,
                    password_changed_at=datetime.now(UTC),
                    must_change_password=False,
                    created_at=datetime.now(UTC),
                    permission_version=0,
                )
            )
            grant_role(session, principal.user_id, next(iter(principal.roles)))
    client.app.dependency_overrides[get_principal] = lambda: principal


def test_export_persists_file_and_metadata(
    json_client: TestClient, api_engine, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CROSSERP_FILES_DIR", str(tmp_path))
    principal = _principal()
    _bind_principal(json_client, principal)

    response = json_client.post(
        "/api/v1/audit/exports",
        json={
            "format": "jsonl",
            "from": "2026-01-01T00:00:00Z",
            "to": "2026-12-31T00:00:00Z",
            "filters": {"action": "test.action"},
        },
        headers={"Idempotency-Key": "audit-export-persist"},
    )
    assert response.status_code == 200
    payload = response.json()

    with Session(api_engine) as session:
        export = session.get(AuditExport, UUID(payload["id"]))
        assert export is not None
        assert export.actor_type == "human"
        assert export.on_behalf_of is None
        assert export.filter_json["filters"] == {"action": "test.action"}
        assert export.status == "ready"
        assert export.file_id is not None
        file_object = session.get(FileObject, export.file_id)
        assert file_object is not None
        content = Path(file_object.storage_path).read_bytes()
        assert hashlib.sha256(content).hexdigest() == export.file_sha256
        assert payload["fileSha256"] == export.file_sha256
        assert export.created_at is not None


def test_export_idempotency_survives_new_app_engine(
    json_client: TestClient, api_engine, monkeypatch, tmp_path: Path, api_database: str
) -> None:
    monkeypatch.setenv("CROSSERP_FILES_DIR", str(tmp_path))
    principal = _principal()
    _bind_principal(json_client, principal)
    first = json_client.post(
        "/api/v1/audit/exports",
        json={"format": "jsonl"},
        headers={"Idempotency-Key": "audit-export-restart"},
    )
    assert first.status_code == 200

    from crosserp.web.app import create_app

    with TestClient(create_app(api_database)) as restarted:
        _bind_principal(restarted, principal)
        downloaded = restarted.get(f"/api/v1/audit/exports/{first.json()['id']}/download")
        assert downloaded.status_code == 200
        assert downloaded.content


def test_tampered_export_is_rejected_and_records_security_event(
    json_client: TestClient, api_engine, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CROSSERP_FILES_DIR", str(tmp_path))
    principal = _principal()
    _bind_principal(json_client, principal)
    created = json_client.post("/api/v1/audit/exports", json={"format": "jsonl"})
    assert created.status_code == 200

    with Session(api_engine) as session:
        export = session.get(AuditExport, UUID(created.json()["id"]))
        assert export is not None and export.file_id is not None
        file_object = session.get(FileObject, export.file_id)
        assert file_object is not None
        Path(file_object.storage_path).write_bytes(b"tampered")

    response = json_client.get(f"/api/v1/audit/exports/{created.json()['id']}/download")
    assert response.status_code == 409
    assert response.json()["code"] == "AUDIT_EXPORT_INTEGRITY_ERROR"
    with Session(api_engine) as session:
        security = session.scalar(
            select(SecurityEvent)
            .where(SecurityEvent.event == "audit_export_tampered")
            .order_by(SecurityEvent.seq.desc())
        )
        assert security is not None
        assert security.user_id == principal.user_id
        reads = list(
            session.scalars(
                select(AuditLog).where(
                    AuditLog.action == "AuditExport.read_download",
                    AuditLog.target_id == str(principal.effective_user_id),
                )
            )
        )
        assert len(reads) == 1


def test_export_download_uses_persisted_acl_and_records_read(
    json_client: TestClient, api_engine
) -> None:
    owner = _principal(role="auditor")
    _bind_principal(json_client, owner)
    created = json_client.post("/api/v1/audit/exports", json={"format": "jsonl"})
    assert created.status_code == 200
    export_id = created.json()["id"]
    _bind_principal(json_client, _principal(role="viewer"))
    assert json_client.get(f"/api/v1/audit/exports/{export_id}/download").status_code == 404
    _bind_principal(json_client, owner)
    assert json_client.get(f"/api/v1/audit/exports/{export_id}/download").status_code == 200
    with Session(api_engine) as session:
        assert (
            session.scalar(
                select(AuditLog).where(
                    AuditLog.action == "AuditExport.read_download",
                    AuditLog.target_id == str(owner.effective_user_id),
                )
            )
            is not None
        )


def test_export_risk_tiers_match_openapi(json_client: TestClient) -> None:
    paths = json_client.app.openapi()["paths"]
    assert paths["/api/v1/audit/exports"]["post"]["x-crosserp"]["riskTier"] == "low"
    assert paths["/api/v1/audit/exports/{id}/download"]["get"]["x-crosserp"]["riskTier"] == "none"


def test_agent_can_execute_low_risk_export_with_inherited_identity(
    json_client: TestClient, api_engine, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CROSSERP_FILES_DIR", str(tmp_path))
    principal = _principal(agent=True)
    _bind_principal(json_client, principal)
    response = json_client.post("/api/v1/audit/exports")
    assert response.status_code == 200
    with Session(api_engine) as session:
        export = session.get(AuditExport, UUID(response.json()["id"]))
        assert export is not None
        assert export.actor_type == "agent"
        assert export.on_behalf_of == principal.on_behalf_of
