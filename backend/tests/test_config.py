from __future__ import annotations

from pathlib import Path

import pytest
from app.config import Settings


def test_settings_load_resource_and_retention_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_DATA_DIR", "custom-runtime")
    monkeypatch.setenv("APP_MAX_UPLOAD_BYTES", "1024")
    monkeypatch.setenv("APP_MAX_MEDIA_PIXELS", "2000000")
    monkeypatch.setenv("APP_MAX_VIDEO_DURATION_SECONDS", "120")
    monkeypatch.setenv("APP_FRAME_INTERVAL_SECONDS", "2.5")
    monkeypatch.setenv("APP_MAX_SAMPLED_FRAMES", "12")
    monkeypatch.setenv("APP_RETENTION_HOURS", "24")
    monkeypatch.setenv("APP_CLEANUP_INTERVAL_SECONDS", "60")

    settings = Settings.from_env()

    assert settings.data_dir == Path("custom-runtime").resolve()
    assert settings.max_upload_bytes == 1024
    assert settings.max_media_pixels == 2_000_000
    assert settings.max_video_duration_seconds == 120
    assert settings.frame_interval_seconds == 2.5
    assert settings.max_sampled_frames == 12
    assert settings.retention_hours == 24
    assert settings.cleanup_interval_seconds == 60


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_upload_bytes", 0),
        ("max_media_pixels", -1),
        ("max_video_duration_seconds", 0),
        ("frame_interval_seconds", 0),
        ("max_sampled_frames", 0),
        ("retention_hours", 0),
        ("cleanup_interval_seconds", -1),
    ],
)
def test_settings_reject_non_positive_limits(
    tmp_path: Path,
    field: str,
    value: int,
) -> None:
    with pytest.raises(ValueError, match=field):
        Settings(data_dir=tmp_path, **{field: value})
