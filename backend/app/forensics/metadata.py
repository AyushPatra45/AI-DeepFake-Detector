from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
from PIL import ExifTags, Image

from app.schemas import MediaType


def _safe_value(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value[:64].hex() + ("..." if len(value) > 64 else "")
    return str(value)[:500]


def extract_metadata(source_path: Path, media_type: MediaType) -> dict:
    if media_type.is_video:
        capture = cv2.VideoCapture(str(source_path))
        if not capture.isOpened():
            return {"parser_warning": "Video metadata could not be decoded"}
        try:
            return {
                "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "frame_rate": round(float(capture.get(cv2.CAP_PROP_FPS)), 3),
                "frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
                "fourcc": _decode_fourcc(int(capture.get(cv2.CAP_PROP_FOURCC))),
            }
        finally:
            capture.release()

    with Image.open(source_path) as image:
        exif = image.getexif()
        exif_values = {
            ExifTags.TAGS.get(tag, str(tag)): _safe_value(value)
            for tag, value in list(exif.items())[:100]
        }
        return {
            "format": image.format,
            "mode": image.mode,
            "width": image.width,
            "height": image.height,
            "exif": exif_values,
        }


def _decode_fourcc(value: int) -> str | None:
    if value <= 0:
        return None
    decoded = "".join(chr((value >> (8 * index)) & 0xFF) for index in range(4))
    return "".join(character for character in decoded if character.isprintable()) or None
