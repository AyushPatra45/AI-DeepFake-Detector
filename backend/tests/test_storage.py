from __future__ import annotations

from pathlib import Path

import pytest
from app.schemas import JobStatus, MediaType
from app.storage import JobNotFoundError, JobRepository


def test_repository_creates_and_updates_job(tmp_path: Path) -> None:
    repository = JobRepository(tmp_path / "jobs.sqlite3")
    source = tmp_path / "source.png"
    source.write_bytes(b"data")

    created = repository.create(
        job_id="job-1",
        source_name="source.png",
        source_path=source,
        media_type=MediaType.PNG,
        sha256="a" * 64,
        size_bytes=4,
    )

    assert created.status == JobStatus.QUEUED
    assert repository.source_path("job-1") == source
    repository.set_status("job-1", JobStatus.PROCESSING)
    assert repository.get("job-1").status == JobStatus.PROCESSING


def test_repository_raises_for_unknown_job(tmp_path: Path) -> None:
    repository = JobRepository(tmp_path / "jobs.sqlite3")
    with pytest.raises(JobNotFoundError):
        repository.get("missing")
