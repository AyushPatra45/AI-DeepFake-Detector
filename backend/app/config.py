from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    max_upload_bytes: int = 500 * 1024 * 1024
    max_media_pixels: int = 40_000_000
    max_video_duration_seconds: float = 2 * 60 * 60
    frame_interval_seconds: float = 1.0
    max_sampled_frames: int = 300
    retention_hours: float = 7 * 24
    cleanup_interval_seconds: float = 60 * 60
    code_version: str = "dev"

    def __post_init__(self) -> None:
        positive_values = {
            "max_upload_bytes": self.max_upload_bytes,
            "max_media_pixels": self.max_media_pixels,
            "max_video_duration_seconds": self.max_video_duration_seconds,
            "frame_interval_seconds": self.frame_interval_seconds,
            "max_sampled_frames": self.max_sampled_frames,
            "retention_hours": self.retention_hours,
            "cleanup_interval_seconds": self.cleanup_interval_seconds,
        }
        invalid = [name for name, value in positive_values.items() if value <= 0]
        if invalid:
            raise ValueError(f"Settings must be greater than zero: {', '.join(invalid)}")

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            data_dir=Path(os.getenv("APP_DATA_DIR", "runtime")).resolve(),
            max_upload_bytes=int(os.getenv("APP_MAX_UPLOAD_BYTES", 500 * 1024 * 1024)),
            max_media_pixels=int(os.getenv("APP_MAX_MEDIA_PIXELS", "40000000")),
            max_video_duration_seconds=float(
                os.getenv("APP_MAX_VIDEO_DURATION_SECONDS", str(2 * 60 * 60))
            ),
            frame_interval_seconds=float(os.getenv("APP_FRAME_INTERVAL_SECONDS", "1.0")),
            max_sampled_frames=int(os.getenv("APP_MAX_SAMPLED_FRAMES", "300")),
            retention_hours=float(os.getenv("APP_RETENTION_HOURS", str(7 * 24))),
            cleanup_interval_seconds=float(
                os.getenv("APP_CLEANUP_INTERVAL_SECONDS", str(60 * 60))
            ),
            code_version=os.getenv("APP_CODE_VERSION", "dev"),
        )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "forensics.sqlite3"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def artifact_dir(self) -> Path:
        return self.data_dir / "artifacts"

    @property
    def report_dir(self) -> Path:
        return self.data_dir / "reports"

    def create_directories(self) -> None:
        for directory in (self.data_dir, self.upload_dir, self.artifact_dir, self.report_dir):
            directory.mkdir(parents=True, exist_ok=True)
