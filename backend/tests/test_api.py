from __future__ import annotations

import hashlib
from io import BytesIO

from app.config import Settings
from app.main import create_app
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


def test_root_redirects_to_api_documentation(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


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
