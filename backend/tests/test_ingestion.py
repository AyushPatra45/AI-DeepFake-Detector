from __future__ import annotations

import pytest
from app.ingestion import InvalidMediaError, detect_media_type
from app.schemas import MediaType


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (b"\xff\xd8\xff\xe0" + b"0" * 20, MediaType.JPEG),
        (b"\x89PNG\r\n\x1a\n" + b"0" * 20, MediaType.PNG),
        (b"\x00\x00\x00\x18ftypisom" + b"0" * 20, MediaType.MP4),
        (b"\x00\x00\x00\x14ftypqt  " + b"0" * 20, MediaType.QUICKTIME),
    ],
)
def test_detect_media_type_uses_content_signature(header: bytes, expected: MediaType) -> None:
    assert detect_media_type(header) == expected


def test_detect_media_type_rejects_unknown_content() -> None:
    with pytest.raises(InvalidMediaError):
        detect_media_type(b"not a supported file")
