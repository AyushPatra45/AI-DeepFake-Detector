from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch
from app.adapters import AnalysisContext
from app.deepfake.adapter import DeepfakeAnalyzer, _candidate_images
from app.deepfake.aggregation import softmax_weighted_score
from app.deepfake.face import FaceCropper
from app.deepfake.model import HybridDeepfakeDetector, RealFFT2D, SRMConv2d
from app.schemas import Artifact, FrameFinding, MediaInfo, MediaType, ModuleStatus


def test_softmax_video_aggregation_emphasises_high_scores() -> None:
    score = softmax_weighted_score([0.1, 0.2, 0.9], temperature=0.1)
    assert 0.85 < score < 0.91
    with pytest.raises(ValueError):
        softmax_weighted_score([])


def test_srm_and_fft_feature_shapes() -> None:
    inputs = torch.rand(1, 3, 32, 32)
    residuals = SRMConv2d()(inputs)
    spectrum = RealFFT2D()(torch.cat([residuals, residuals[:, :1]], dim=1))

    assert residuals.shape == (1, 9, 32, 32)
    assert spectrum.shape == (1, 20, 32, 32)
    assert torch.isfinite(spectrum).all()


def test_hybrid_model_returns_one_logit() -> None:
    model = HybridDeepfakeDetector().eval()
    with torch.inference_mode():
        output = model(torch.rand(1, 3, 64, 64))
    assert output.shape == (1, 1)


def test_missing_checkpoint_is_explicitly_skipped(tmp_path: Path) -> None:
    source = tmp_path / "image.png"
    source.write_bytes(b"unused because checkpoint is checked first")
    analyzer = DeepfakeAnalyzer(checkpoint_path=tmp_path / "missing.pth")
    context = AnalysisContext(
        job_id="job-1",
        source_path=source,
        artifact_dir=tmp_path / "artifacts",
        media=MediaInfo(media_type=MediaType.PNG, width=10, height=10),
        frames=[],
    )

    result = analyzer.analyse(context)

    assert result.status == ModuleStatus.SKIPPED
    assert "checkpoint" in result.warnings[0].lower()


def test_face_cropper_returns_none_when_no_face_is_present() -> None:
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    assert FaceCropper(target_size=64).crop_largest(image) is None


def test_video_candidates_resolve_only_generated_frame_names(tmp_path: Path) -> None:
    frame = FrameFinding(
        frame_index=5,
        timestamp_seconds=0.5,
        artifact=Artifact(kind="sampled_frame", path="/artifacts/job-1/frame-0001.jpg"),
    )
    context = AnalysisContext(
        job_id="job-1",
        source_path=tmp_path / "video.mp4",
        artifact_dir=tmp_path / "job-1",
        media=MediaInfo(media_type=MediaType.MP4, width=100, height=100),
        frames=[frame],
    )

    assert _candidate_images(context) == [(tmp_path / "job-1" / "frame-0001.jpg", frame)]
