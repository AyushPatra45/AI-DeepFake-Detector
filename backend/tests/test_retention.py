from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.config import Settings
from app.retention import RetentionManager, cleanup_expired_jobs
from app.schemas import JobStatus, MediaType
from app.storage import JobNotFoundError, JobRepository


def _settings(tmp_path: Path) -> Settings:
    settings = Settings(
        data_dir=tmp_path / "runtime",
        retention_hours=1,
        cleanup_interval_seconds=60,
    )
    settings.create_directories()
    return settings


def _create_job(
    repository: JobRepository,
    settings: Settings,
    job_id: str,
    status: JobStatus,
    *,
    source_path: Path | None = None,
) -> Path:
    source = source_path or settings.upload_dir / f"{job_id}.png"
    source.write_bytes(b"media")
    repository.create(
        job_id=job_id,
        source_name=f"{job_id}.png",
        source_path=source,
        media_type=MediaType.PNG,
        sha256="a" * 64,
        size_bytes=5,
    )
    repository.set_status(job_id, status)
    return source


def _age_job(repository: JobRepository, job_id: str, timestamp: datetime) -> None:
    with closing(sqlite3.connect(repository.database_path)) as connection:
        connection.execute(
            "UPDATE analysis_jobs SET created_at = ?, updated_at = ? WHERE id = ?",
            (timestamp.isoformat(), timestamp.isoformat(), job_id),
        )
        connection.commit()


def test_cleanup_removes_expired_terminal_job_files_and_stale_parts(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    repository = JobRepository(settings.database_path)
    now = datetime(2026, 9, 11, 12, tzinfo=UTC)
    source = _create_job(repository, settings, "expired", JobStatus.FAILED)
    _age_job(repository, "expired", now - timedelta(hours=2))
    artifact_dir = settings.artifact_dir / "expired"
    artifact_dir.mkdir()
    (artifact_dir / "heatmap.png").write_bytes(b"artifact")
    json_report = settings.report_dir / "expired.json"
    pdf_report = settings.report_dir / "expired.pdf"
    json_report.write_bytes(b"{}")
    pdf_report.write_bytes(b"%PDF")
    part = settings.upload_dir / "abandoned.part"
    part.write_bytes(b"partial")
    old_timestamp = (now - timedelta(hours=2)).timestamp()
    os.utime(part, (old_timestamp, old_timestamp))

    result = cleanup_expired_jobs(repository, settings, now=now)

    assert result.deleted_jobs == ["expired"]
    assert result.failed_jobs == {}
    assert result.deleted_temporary_uploads == 1
    assert not source.exists()
    assert not artifact_dir.exists()
    assert not json_report.exists()
    assert not pdf_report.exists()
    assert not part.exists()
    with pytest.raises(JobNotFoundError):
        repository.get("expired")


def test_cleanup_preserves_active_and_recent_jobs(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    repository = JobRepository(settings.database_path)
    now = datetime(2026, 9, 11, 12, tzinfo=UTC)
    active = _create_job(repository, settings, "active", JobStatus.PROCESSING)
    recent = _create_job(repository, settings, "recent", JobStatus.FAILED)
    _age_job(repository, "active", now - timedelta(days=2))
    _age_job(repository, "recent", now - timedelta(minutes=30))

    result = cleanup_expired_jobs(repository, settings, now=now)

    assert result.expired_jobs == 0
    assert active.exists()
    assert recent.exists()
    assert repository.get("active").status == JobStatus.PROCESSING
    assert repository.get("recent").status == JobStatus.FAILED


def test_cleanup_refuses_source_path_outside_upload_root(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    repository = JobRepository(settings.database_path)
    now = datetime(2026, 9, 11, 12, tzinfo=UTC)
    external = tmp_path / "external.png"
    _create_job(
        repository,
        settings,
        "unsafe",
        JobStatus.FAILED,
        source_path=external,
    )
    _age_job(repository, "unsafe", now - timedelta(hours=2))

    result = cleanup_expired_jobs(repository, settings, now=now)

    assert "unsafe" in result.failed_jobs
    assert external.exists()
    assert repository.get("unsafe").status == JobStatus.FAILED


def test_retention_manager_respects_cleanup_interval(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    repository = JobRepository(settings.database_path)
    ticks = iter([0.0, 30.0, 61.0])
    manager = RetentionManager(repository, settings, clock=lambda: next(ticks))

    assert manager.run_if_due() is not None
    assert manager.run_if_due() is None
    assert manager.run_if_due() is not None
