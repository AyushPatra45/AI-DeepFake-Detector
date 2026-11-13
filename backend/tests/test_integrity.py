from __future__ import annotations

import hashlib

import pytest
from app.config import Settings
from app.orchestrator import process_job
from app.schemas import JobStatus, MediaType
from app.storage import JobRepository
from PIL import Image


@pytest.mark.parametrize("changed", [False, True])
def test_source_integrity_is_checked_before_analysis(settings: Settings, changed: bool) -> None:
    settings.create_directories()
    source = settings.upload_dir / "source.png"
    Image.new("RGB", (16, 16), "red").save(source)
    original = source.read_bytes()
    repository = JobRepository(settings.database_path)
    repository.create(
        job_id="integrity", source_name=source.name, source_path=source,
        media_type=MediaType.PNG, sha256=hashlib.sha256(original).hexdigest(),
        size_bytes=len(original),
    )
    if changed:
        Image.new("RGB", (16, 16), "blue").save(source)
    process_job("integrity", repository, settings, [])
    job = repository.get("integrity")
    if changed:
        assert job.status == JobStatus.FAILED
        assert "SHA-256 differs" in job.error
        assert job.result is None
    else:
        assert job.status == JobStatus.COMPLETED
        assert job.result.modules[0].findings["sha256_verified"] is True
