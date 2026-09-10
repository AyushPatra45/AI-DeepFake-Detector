from __future__ import annotations

import shutil
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic

from app.config import Settings
from app.storage import JobRepository, StoredJob


@dataclass
class CleanupResult:
    cutoff: datetime
    expired_jobs: int = 0
    deleted_jobs: list[str] = field(default_factory=list)
    failed_jobs: dict[str, str] = field(default_factory=dict)
    deleted_temporary_uploads: int = 0


def _contained(path: Path, root: Path) -> Path:
    resolved_root = root.resolve()
    resolved_path = path.resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(f"Refusing to remove path outside {resolved_root}") from error
    return resolved_path


def _validate_file(path: Path, root: Path) -> Path:
    safe_path = _contained(path, root)
    if safe_path.exists() and not safe_path.is_file():
        raise ValueError(f"Expected a file during retention cleanup: {safe_path}")
    return safe_path


def _validate_directory(path: Path, root: Path) -> Path:
    safe_path = _contained(path, root)
    if safe_path.exists() and not safe_path.is_dir():
        raise ValueError(f"Expected a directory during retention cleanup: {safe_path}")
    return safe_path


def _remove_file(safe_path: Path) -> None:
    if safe_path.exists():
        safe_path.unlink()


def _remove_directory(safe_path: Path) -> None:
    if safe_path.exists():
        shutil.rmtree(safe_path)


def _remove_job_files(job: StoredJob, settings: Settings) -> None:
    source_path = _validate_file(job.source_path, settings.upload_dir)
    artifact_path = _validate_directory(
        settings.artifact_dir / job.id,
        settings.artifact_dir,
    )
    json_report_path = _validate_file(
        settings.report_dir / f"{job.id}.json",
        settings.report_dir,
    )
    pdf_report_path = _validate_file(
        settings.report_dir / f"{job.id}.pdf",
        settings.report_dir,
    )

    _remove_file(source_path)
    _remove_directory(artifact_path)
    _remove_file(json_report_path)
    _remove_file(pdf_report_path)


def cleanup_expired_jobs(
    repository: JobRepository,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> CleanupResult:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("Cleanup time must be timezone-aware")
    cutoff = current.astimezone(UTC) - timedelta(hours=settings.retention_hours)
    expired = repository.expired_before(cutoff)
    result = CleanupResult(cutoff=cutoff, expired_jobs=len(expired))

    for job in expired:
        try:
            _remove_job_files(job, settings)
            repository.delete(job.id)
            result.deleted_jobs.append(job.id)
        except Exception as exc:
            result.failed_jobs[job.id] = f"{type(exc).__name__}: {exc}"

    cutoff_timestamp = cutoff.timestamp()
    for temporary_path in settings.upload_dir.glob("*.part"):
        try:
            safe_path = _contained(temporary_path, settings.upload_dir)
            if safe_path.is_file() and safe_path.stat().st_mtime < cutoff_timestamp:
                safe_path.unlink()
                result.deleted_temporary_uploads += 1
        except OSError:
            continue
    return result


class RetentionManager:
    def __init__(
        self,
        repository: JobRepository,
        settings: Settings,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.clock = clock
        self._last_run: float | None = None
        self._lock = threading.Lock()
        self.last_result: CleanupResult | None = None

    def run_if_due(self, *, force: bool = False) -> CleanupResult | None:
        current_tick = self.clock()
        with self._lock:
            if (
                not force
                and self._last_run is not None
                and current_tick - self._last_run < self.settings.cleanup_interval_seconds
            ):
                return None
            result = cleanup_expired_jobs(self.repository, self.settings)
            self._last_run = current_tick
            self.last_result = result
            return result
