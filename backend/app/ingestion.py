from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.schemas import MediaType

CHUNK_SIZE = 1024 * 1024


class InvalidMediaError(ValueError):
    pass


class UploadTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class IngestedMedia:
    source_name: str
    path: Path
    media_type: MediaType
    sha256: str
    size_bytes: int


def detect_media_type(header: bytes) -> MediaType:
    if header.startswith(b"\xff\xd8\xff"):
        return MediaType.JPEG
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return MediaType.PNG
    if len(header) >= 12 and header[4:8] == b"ftyp":
        brand = header[8:12]
        if brand == b"qt  ":
            return MediaType.QUICKTIME
        return MediaType.MP4
    raise InvalidMediaError("Unsupported or unrecognised media content")


def _extension(media_type: MediaType) -> str:
    return {
        MediaType.JPEG: ".jpg",
        MediaType.PNG: ".png",
        MediaType.MP4: ".mp4",
        MediaType.QUICKTIME: ".mov",
    }[media_type]


async def save_upload(
    upload: UploadFile,
    *,
    job_id: str,
    upload_dir: Path,
    max_bytes: int,
) -> IngestedMedia:
    source_name = Path(upload.filename or "unnamed").name
    if source_name in {"", ".", ".."}:
        source_name = "unnamed"

    upload_dir.mkdir(parents=True, exist_ok=True)
    temporary_path = upload_dir / f"{job_id}.part"
    digest = hashlib.sha256()
    size = 0
    header = b""

    try:
        with temporary_path.open("xb") as destination:
            while chunk := await upload.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_bytes:
                    raise UploadTooLargeError(f"Upload exceeds {max_bytes} bytes")
                if len(header) < 32:
                    header = (header + chunk)[:32]
                digest.update(chunk)
                destination.write(chunk)

        if size == 0:
            raise InvalidMediaError("Uploaded file is empty")
        media_type = detect_media_type(header)
        final_path = upload_dir / f"{job_id}{_extension(media_type)}"
        temporary_path.replace(final_path)
        return IngestedMedia(
            source_name=source_name,
            path=final_path,
            media_type=media_type,
            sha256=digest.hexdigest(),
            size_bytes=size,
        )
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
