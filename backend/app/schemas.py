from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class MediaType(StrEnum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    MP4 = "video/mp4"
    QUICKTIME = "video/quicktime"

    @property
    def is_video(self) -> bool:
        return self in {MediaType.MP4, MediaType.QUICKTIME}


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partially_completed"
    FAILED = "failed"


class ModuleStatus(StrEnum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class Artifact(BaseModel):
    kind: str
    path: str
    description: str | None = None


class ModuleResult(BaseModel):
    module: str
    status: ModuleStatus
    version: str
    settings: dict[str, Any] = Field(default_factory=dict)
    findings: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[Artifact] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    duration_ms: int = 0


class FrameFinding(BaseModel):
    frame_index: int
    timestamp_seconds: float
    artifact: Artifact
    deepfake_probability: float | None = Field(default=None, ge=0, le=1)
    face_id: str | None = None


class MediaInfo(BaseModel):
    media_type: MediaType
    width: int
    height: int
    duration_seconds: float | None = None
    frame_rate: float | None = None
    frame_count: int | None = None


class AnalysisResult(BaseModel):
    job_id: str
    source_sha256: str
    code_version: str
    analysed_at: datetime = Field(default_factory=utc_now)
    media: MediaInfo
    modules: list[ModuleResult]
    frames: list[FrameFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class JobView(BaseModel):
    id: str
    status: JobStatus
    source_name: str
    media_type: MediaType
    sha256: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime
    error: str | None = None
    result: AnalysisResult | None = None


class JobList(BaseModel):
    jobs: list[JobView]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
