from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "runtime",
        max_upload_bytes=2 * 1024 * 1024,
        frame_interval_seconds=0.5,
        max_sampled_frames=5,
        code_version="test-version",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
