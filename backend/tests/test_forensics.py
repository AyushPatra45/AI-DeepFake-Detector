from __future__ import annotations

from pathlib import Path

import numpy as np
from app.adapters import AnalysisContext
from app.forensics.adapter import ImageForensicsAnalyzer
from app.forensics.ela import generate_ela
from app.forensics.lsb import MARKER, analyse_lsb
from app.forensics.metadata import extract_metadata
from app.schemas import MediaInfo, MediaType, ModuleStatus
from PIL import Image


def _write_lsb_image(path: Path, payload: bytes) -> None:
    pixels = np.full((64, 64, 3), 128, dtype=np.uint8)
    encoded = MARKER + payload + b"\x00"
    bits = np.unpackbits(np.frombuffer(encoded, dtype=np.uint8), bitorder="big")
    flattened = pixels.reshape(-1)
    flattened[: len(bits)] = (flattened[: len(bits)] & 0xFE) | bits
    Image.fromarray(pixels, mode="RGB").save(path, format="PNG")


def test_ela_generates_measured_heatmap(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    output = tmp_path / "ela.png"
    pixels = np.zeros((40, 50, 3), dtype=np.uint8)
    pixels[10:30, 15:35] = (220, 30, 30)
    Image.fromarray(pixels, mode="RGB").save(source, format="JPEG", quality=82)

    result = generate_ela(source, output, jpeg_quality=90)

    assert output.exists()
    assert result.jpeg_quality == 90
    assert result.max_error >= 0
    assert 0 <= result.highlighted_pixel_ratio <= 1


def test_lsb_extracts_supported_marker_payload_as_bytes(tmp_path: Path) -> None:
    source = tmp_path / "stego.png"
    _write_lsb_image(source, b"review-one-secret")

    result = analyse_lsb(source)

    assert result.extracted_payload == b"review-one-secret"
    assert result.findings["supported_payload_detected"] is True
    assert result.findings["extraction_method"] == "STEGv1 marker"
    assert set(result.findings["channel_statistics"]) == {"red", "green", "blue"}


def test_image_forensics_adapter_returns_artifacts_and_metadata(tmp_path: Path) -> None:
    source = tmp_path / "stego.png"
    artifact_dir = tmp_path / "artifacts"
    _write_lsb_image(source, b"safe payload")
    context = AnalysisContext(
        job_id="job-1",
        source_path=source,
        artifact_dir=artifact_dir,
        media=MediaInfo(media_type=MediaType.PNG, width=64, height=64),
        frames=[],
    )

    result = ImageForensicsAnalyzer().analyse(context)

    assert result.status == ModuleStatus.COMPLETED
    assert result.findings["metadata"]["format"] == "PNG"
    assert result.findings["lsb"]["supported_payload_detected"] is True
    assert {artifact.kind for artifact in result.artifacts} == {
        "ela_heatmap",
        "extracted_payload",
    }
    assert (artifact_dir / "ela-heatmap.png").exists()
    assert (artifact_dir / "extracted-lsb-payload.bin").read_bytes() == b"safe payload"


def test_metadata_reports_basic_image_properties(tmp_path: Path) -> None:
    source = tmp_path / "image.png"
    Image.new("RGB", (12, 8), color="white").save(source)

    metadata = extract_metadata(source, MediaType.PNG)

    assert metadata["format"] == "PNG"
    assert metadata["width"] == 12
    assert metadata["height"] == 8
