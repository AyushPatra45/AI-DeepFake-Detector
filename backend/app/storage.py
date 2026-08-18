from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.schemas import AnalysisResult, JobStatus, JobView, MediaType


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()


class JobNotFoundError(LookupError):
    pass


class JobRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialise(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error TEXT,
                    result_json TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON analysis_jobs(created_at DESC)"
            )

    def create(
        self,
        *,
        job_id: str,
        source_name: str,
        source_path: Path,
        media_type: MediaType,
        sha256: str,
        size_bytes: int,
    ) -> JobView:
        now = _utc_iso()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO analysis_jobs (
                    id, status, source_name, source_path, media_type, sha256,
                    size_bytes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    JobStatus.QUEUED,
                    source_name,
                    str(source_path),
                    media_type,
                    sha256,
                    size_bytes,
                    now,
                    now,
                ),
            )
        return self.get(job_id)

    def get(self, job_id: str) -> JobView:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM analysis_jobs WHERE id = ?", (job_id,)
            ).fetchone()
        if row is None:
            raise JobNotFoundError(job_id)
        return self._to_view(row)

    def source_path(self, job_id: str) -> Path:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT source_path FROM analysis_jobs WHERE id = ?", (job_id,)
            ).fetchone()
        if row is None:
            raise JobNotFoundError(job_id)
        return Path(row["source_path"])

    def list(self, limit: int = 50) -> list[JobView]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM analysis_jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._to_view(row) for row in rows]

    def set_status(self, job_id: str, status: JobStatus) -> None:
        self._update(job_id, status=status)

    def complete(self, job_id: str, result: AnalysisResult, *, partial: bool = False) -> None:
        status = JobStatus.PARTIAL if partial else JobStatus.COMPLETED
        self._update(job_id, status=status, result_json=result.model_dump_json())

    def fail(self, job_id: str, error: str) -> None:
        self._update(job_id, status=JobStatus.FAILED, error=error[:1000])

    def _update(
        self,
        job_id: str,
        *,
        status: JobStatus,
        result_json: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE analysis_jobs
                SET status = ?, result_json = COALESCE(?, result_json),
                    error = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, result_json, error, _utc_iso(), job_id),
            )
            if cursor.rowcount == 0:
                raise JobNotFoundError(job_id)

    @staticmethod
    def _to_view(row: sqlite3.Row) -> JobView:
        result_data = json.loads(row["result_json"]) if row["result_json"] else None
        return JobView(
            id=row["id"],
            status=JobStatus(row["status"]),
            source_name=row["source_name"],
            media_type=MediaType(row["media_type"]),
            sha256=row["sha256"],
            size_bytes=row["size_bytes"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            error=row["error"],
            result=AnalysisResult.model_validate(result_data) if result_data else None,
        )
