from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from app.adapters import AnalysisContext
from app.authenticity.adapter import MediaAuthenticityAnalyzer
from app.authenticity.provenance import scan_provenance_markers
from app.authenticity.watermark import detect_google_sparkle
from app.schemas import Artifact, FrameFinding, MediaInfo, MediaType, ModuleStatus


def _write_frame(path: Path, *, watermark: bool, phase: int = 0) -> None:
    image = np.full(
        (360, 640, 3),
        (50 + phase * 12, 75 + phase * 8, 100 + phase * 5),
        dtype=np.uint8,
    )
    shift = phase * 35
    cv2.rectangle(
        image,
        (40 + shift, 40),
        (260 + shift, 260),
        (100, 130 + phase * 8, 160),
        -1,
    )
    if watermark:
        center_x, center_y = 580, 300
        points = np.array(
            [
                (center_x, center_y - 28),
                (center_x + 8, center_y - 8),
                (center_x + 28, center_y),
                (center_x + 8, center_y + 8),
                (center_x, center_y + 28),
                (center_x - 8, center_y + 8),
                (center_x - 28, center_y),
                (center_x - 8, center_y - 8),
            ],
            dtype=np.int32,
        )
        cv2.fillPoly(image, [points], (220, 220, 220))
    assert cv2.imwrite(str(path), image)


def test_temporally_persistent_sparkle_watermark_is_detected(tmp_path: Path) -> None:
    frames = []
    for index in range(4):
        path = tmp_path / f"frame-{index}.jpg"
        _write_frame(path, watermark=True, phase=index)
        frames.append(path)

    result = detect_google_sparkle(frames, artifact_path=tmp_path / "evidence.png")

    assert result.candidate_detected is True
    assert result.location == "bottom_right"
    assert result.match_score >= 0.60
    assert result.artifact_path == tmp_path / "evidence.png"
    assert result.artifact_path.exists()


def test_plain_frames_do_not_create_watermark_evidence(tmp_path: Path) -> None:
    frames = []
    for index in range(4):
        path = tmp_path / f"plain-{index}.jpg"
        _write_frame(path, watermark=False, phase=index)
        frames.append(path)

    result = detect_google_sparkle(frames, artifact_path=tmp_path / "evidence.png")

    assert result.candidate_detected is False
    assert result.artifact_path is None
    assert not (tmp_path / "evidence.png").exists()


def test_provenance_scan_reports_c2pa_and_provider_markers(tmp_path: Path) -> None:
    media = tmp_path / "media.bin"
    media.write_bytes(
        b"prefix C2PA manifest Created by Google Generative AI Gemini "
        b"trainedAlgorithmicMedia suffix"
    )

    result = scan_provenance_markers(media)

    assert result["c2pa_marker_detected"] is True
    assert result["ai_origin_claim_detected"] is True
    assert "Created by Google Generative AI" in result["ai_origin_claims"]
    assert result["provider_markers"] == ["Google Gemini", "Google Generative AI"]


def test_generic_c2pa_marker_is_not_treated_as_an_ai_origin_claim(tmp_path: Path) -> None:
    media = tmp_path / "camera.jpg"
    media.write_bytes(b"C2PA camera provenance manifest")

    result = scan_provenance_markers(media)

    assert result["c2pa_marker_detected"] is True
    assert result["ai_origin_claim_detected"] is False


def test_visible_watermark_text_alone_is_not_an_ai_claim(tmp_path: Path) -> None:
    source = tmp_path / "copyright.bin"
    source.write_bytes(b"photographer added visible watermark")
    assert scan_provenance_markers(source)["ai_origin_claim_detected"] is False


def test_copied_ai_claim_is_not_strong_origin_evidence(tmp_path: Path) -> None:
    source = tmp_path / "claim.png"
    _write_frame(source, watermark=False)
    with source.open("ab") as file:
        file.write(b" C2PA trainedAlgorithmicMedia")
    result = MediaAuthenticityAnalyzer().analyse(AnalysisContext(
        job_id="claim", source_path=source, artifact_dir=tmp_path / "artifacts",
        media=MediaInfo(media_type=MediaType.PNG, width=640, height=360), frames=[],
    ))
    assert result.findings["assessment"] == "unverified_ai_origin_claim"
    assert result.findings["provenance"]["signature_verified"] is False
    assert any("not verified" in warning for warning in result.warnings)


def test_watermark_sampling_is_bounded_and_spans_input(tmp_path: Path, monkeypatch) -> None:
    import app.authenticity.watermark as module

    paths = [tmp_path / f"{index}.jpg" for index in range(300)]
    reads = []

    def read(path):
        reads.append(path)
        return np.zeros((100, 200, 3), dtype=np.uint8)

    monkeypatch.setattr(module.cv2, "imread", read)
    result = module.detect_google_sparkle(paths, artifact_path=tmp_path / "evidence.png")
    assert result.analysed_frames == module.MAX_WATERMARK_FRAMES
    assert reads[0] == str(paths[0])
    assert reads[-1] == str(paths[-1])


def test_no_readable_watermark_frames(tmp_path: Path) -> None:
    for paths in ([], [tmp_path / "missing.jpg"]):
        result = detect_google_sparkle(paths, artifact_path=tmp_path / "evidence.png")
        assert result.analysed_frames == 0
        assert result.candidate_detected is False


def test_authenticity_adapter_reports_strong_video_origin_evidence(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    frames = []
    for index in range(4):
        filename = f"frame-{index}.jpg"
        _write_frame(artifact_dir / filename, watermark=True, phase=index)
        frames.append(
            FrameFinding(
                frame_index=index,
                timestamp_seconds=float(index),
                artifact=Artifact(kind="sampled_frame", path=f"/artifacts/job/{filename}"),
            )
        )
    source = tmp_path / "video.mp4"
    source.write_bytes(b"video without textual provenance markers")
    context = AnalysisContext(
        job_id="job",
        source_path=source,
        artifact_dir=artifact_dir,
        media=MediaInfo(media_type=MediaType.MP4, width=640, height=360),
        frames=frames,
    )

    result = MediaAuthenticityAnalyzer().analyse(context)

    assert result.status == ModuleStatus.COMPLETED
    assert result.findings["assessment"] == "strong_ai_origin_evidence"
    assert result.findings["visible_watermark"]["candidate_detected"] is True
    assert result.artifacts[0].kind == "visible_watermark_evidence"
