from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    max_upload_bytes: int = 500 * 1024 * 1024
    frame_interval_seconds: float = 1.0
    max_sampled_frames: int = 300
    code_version: str = "dev"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            data_dir=Path(os.getenv("APP_DATA_DIR", "runtime")).resolve(),
            max_upload_bytes=int(os.getenv("APP_MAX_UPLOAD_BYTES", 500 * 1024 * 1024)),
            frame_interval_seconds=float(os.getenv("APP_FRAME_INTERVAL_SECONDS", "1.0")),
            max_sampled_frames=int(os.getenv("APP_MAX_SAMPLED_FRAMES", "300")),
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
