from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

from app.config import Settings
from app.main import create_app
from app.schemas import JobStatus, MediaType
from app.storage import JobRepository
from fastapi.testclient import TestClient
from PIL import Image


def png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (24, 16), color=(30, 120, 190)).save(output, format="PNG")
    return output.getvalue()


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "test-version"}


def test_root_serves_forensic_workspace(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "AI-Powered Deepfake" in response.text
    assert client.get("/static/app.js").status_code == 200


def test_image_analysis_and_reports(client: TestClient) -> None:
    content = png_bytes()
    created = client.post(
        "/api/v1/analyses",
        files={"file": ("../unsafe-name.png", content, "image/png")},
    )

    assert created.status_code == 202
    job_id = created.json()["id"]
    completed = client.get(f"/api/v1/analyses/{job_id}")
    payload = completed.json()
    assert completed.status_code == 200
    assert payload["status"] == "partially_completed"
    assert payload["source_name"] == "unsafe-name.png"
    assert payload["sha256"] == hashlib.sha256(content).hexdigest()
    assert payload["result"]["media"]["width"] == 24
    assert payload["result"]["media"]["height"] == 16
    assert [module["module"] for module in payload["result"]["modules"]] == [
        "platform_ingestion",
        "deepfake_detection",
        "image_forensics",
    ]

    json_report = client.get(f"/api/v1/analyses/{job_id}/report.json")
    assert json_report.status_code == 200
    assert json_report.json()["report_type"] == "forensic-risk-assessment"

    pdf_report = client.get(f"/api/v1/analyses/{job_id}/report.pdf")
    assert pdf_report.status_code == 200
    assert pdf_report.content.startswith(b"%PDF")


def test_rejects_unsupported_content(client: TestClient) -> None:
    response = client.post(
        "/api/v1/analyses",
        files={"file": ("fake.jpg", b"this is not an image", "image/jpeg")},
    )
    assert response.status_code == 415


def test_rejects_upload_over_configured_limit(settings: Settings) -> None:
    settings = Settings(
        data_dir=settings.data_dir,
        max_upload_bytes=8,
        frame_interval_seconds=settings.frame_interval_seconds,
        max_sampled_frames=settings.max_sampled_frames,
        code_version=settings.code_version,
    )
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/analyses",
            files={"file": ("large.png", png_bytes(), "image/png")},
        )
    assert response.status_code == 413


def test_lists_jobs_and_returns_not_found(client: TestClient) -> None:
    client.post(
        "/api/v1/analyses",
        files={"file": ("sample.png", png_bytes(), "image/png")},
    )
    listing = client.get("/api/v1/analyses")
    assert listing.status_code == 200
    assert len(listing.json()["jobs"]) == 1
    assert client.get("/api/v1/analyses/missing").status_code == 404


def test_application_startup_cleans_expired_jobs(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path / "runtime",
        retention_hours=1,
        cleanup_interval_seconds=60,
    )
    settings.create_directories()
    repository = JobRepository(settings.database_path)
    source = settings.upload_dir / "expired.png"
    source.write_bytes(png_bytes())
    repository.create(
        job_id="expired",
        source_name="expired.png",
        source_path=source,
        media_type=MediaType.PNG,
        sha256="b" * 64,
        size_bytes=source.stat().st_size,
    )
    repository.set_status("expired", JobStatus.FAILED)
    expired_at = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    with closing(sqlite3.connect(settings.database_path)) as connection:
        connection.execute(
            "UPDATE analysis_jobs SET created_at = ?, updated_at = ? WHERE id = ?",
            (expired_at, expired_at, "expired"),
        )
        connection.commit()

    with TestClient(create_app(settings)) as cleanup_client:
        assert cleanup_client.get("/api/v1/analyses/expired").status_code == 404

    assert not source.exists()
