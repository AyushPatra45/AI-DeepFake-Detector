from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from app.media import MediaLimitError, inspect_image, sample_video
from app.schemas import MediaType
from PIL import Image


def _write_test_video(path: Path) -> bool:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10.0,
        (32, 24),
    )
    if not writer.isOpened():
        return False
    for index in range(20):
        frame = np.full((24, 32, 3), index * 10, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return True


def test_video_sampling_preserves_timestamps_and_limit(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mp4"
    if not _write_test_video(video_path):
        pytest.skip("MP4 encoder is unavailable in this OpenCV build")

    inspected = sample_video(
        video_path,
        MediaType.MP4,
        output_dir=tmp_path / "frames",
        interval_seconds=0.5,
        max_frames=3,
    )

    assert inspected.info.width == 32
    assert inspected.info.height == 24
    assert inspected.info.duration_seconds == pytest.approx(2.0, abs=0.2)
    assert [frame.timestamp_seconds for frame in inspected.frames] == [0.0, 0.5, 1.0]
    assert all(
        (tmp_path / "frames" / Path(frame.artifact.path).name).exists()
        for frame in inspected.frames
    )
    assert inspected.warnings == ["Sampling stopped at the configured limit of 3 frames"]


def test_image_pixel_limit_is_enforced_before_analysis(tmp_path: Path) -> None:
    image_path = tmp_path / "large.png"
    Image.new("RGB", (20, 20)).save(image_path)

    with pytest.raises(MediaLimitError, match="100 pixels"):
        inspect_image(image_path, MediaType.PNG, max_pixels=100)


def test_video_duration_limit_is_enforced(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mp4"
    if not _write_test_video(video_path):
        pytest.skip("MP4 encoder is unavailable in this OpenCV build")

    with pytest.raises(MediaLimitError, match="1 seconds"):
        sample_video(
            video_path,
            MediaType.MP4,
            output_dir=tmp_path / "frames",
            interval_seconds=0.5,
            max_frames=3,
            max_duration_seconds=1,
        )

    assert not (tmp_path / "frames").exists()
