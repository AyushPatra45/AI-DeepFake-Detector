from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
from PIL import Image, UnidentifiedImageError

from app.schemas import Artifact, FrameFinding, MediaInfo, MediaType


class MediaDecodeError(RuntimeError):
    pass


@dataclass(frozen=True)
class InspectedMedia:
    info: MediaInfo
    frames: list[FrameFinding]
    warnings: list[str]


def inspect_image(path: Path, media_type: MediaType) -> InspectedMedia:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise MediaDecodeError("Image content could not be decoded") from exc

    return InspectedMedia(
        info=MediaInfo(media_type=media_type, width=width, height=height),
        frames=[],
        warnings=[],
    )


def sample_video(
    path: Path,
    media_type: MediaType,
    *,
    output_dir: Path,
    interval_seconds: float,
    max_frames: int,
) -> InspectedMedia:
    if interval_seconds <= 0:
        raise ValueError("Frame interval must be greater than zero")
    if max_frames <= 0:
        raise ValueError("Maximum sampled frames must be greater than zero")

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise MediaDecodeError("Video content could not be decoded")

    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if fps <= 0 or total_frames <= 0 or width <= 0 or height <= 0:
            raise MediaDecodeError("Video metadata is incomplete or invalid")

        duration = total_frames / fps
        output_dir.mkdir(parents=True, exist_ok=True)
        samples: list[FrameFinding] = []
        timestamp = 0.0

        while timestamp < duration and len(samples) < max_frames:
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ok, frame = capture.read()
            if not ok:
                timestamp += interval_seconds
                continue

            frame_index = min(round(timestamp * fps), total_frames - 1)
            file_name = f"frame-{len(samples):04d}-{frame_index}.jpg"
            frame_path = output_dir / file_name
            if not cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 92]):
                raise MediaDecodeError("A sampled frame could not be saved")

            samples.append(
                FrameFinding(
                    frame_index=frame_index,
                    timestamp_seconds=round(timestamp, 3),
                    artifact=Artifact(
                        kind="sampled_frame",
                        path=f"/artifacts/{output_dir.name}/{file_name}",
                        description="Frame selected by the configured sampling policy",
                    ),
                )
            )
            timestamp += interval_seconds

        warnings: list[str] = []
        expected_samples = max(1, int(duration / interval_seconds) + 1)
        if len(samples) >= max_frames and expected_samples > max_frames:
            warnings.append(f"Sampling stopped at the configured limit of {max_frames} frames")
        if not samples:
            raise MediaDecodeError("No frames could be sampled from the video")

        return InspectedMedia(
            info=MediaInfo(
                media_type=media_type,
                width=width,
                height=height,
                duration_seconds=round(duration, 3),
                frame_rate=round(fps, 3),
                frame_count=total_frames,
            ),
            frames=samples,
            warnings=warnings,
        )
    finally:
        capture.release()


def inspect_media(
    path: Path,
    media_type: MediaType,
    *,
    output_dir: Path,
    interval_seconds: float,
    max_frames: int,
) -> InspectedMedia:
    if media_type.is_video:
        return sample_video(
            path,
            media_type,
            output_dir=output_dir,
            interval_seconds=interval_seconds,
            max_frames=max_frames,
        )
    return inspect_image(path, media_type)
