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


def test_evaluation_manifest_generation_and_disjointness(tmp_path: Path) -> None:
    from evaluation.deepfake.manifests import (
        DatasetManifest,
        check_identity_disjointness,
        generate_benchmark_manifests,
    )

    manifest_paths = generate_benchmark_manifests(tmp_path / "manifests")
    ffpp_manifest = DatasetManifest.load(manifest_paths["ffpp_indomain_test"])
    celeb_manifest = DatasetManifest.load(manifest_paths["celebdf_cross_test"])

    assert ffpp_manifest.total == 100
    assert ffpp_manifest.num_real == 50
    assert ffpp_manifest.num_fake == 50
    assert celeb_manifest.total == 50

    is_disjoint, overlapping = check_identity_disjointness(ffpp_manifest, celeb_manifest)
    assert is_disjoint
    assert len(overlapping) == 0


def test_evaluator_metrics_computation() -> None:
    from evaluation.deepfake.evaluator import (
        ManifestItem,
        compute_auc_roc,
        compute_ece,
        evaluate_predictions,
    )

    labels = [0, 0, 1, 1]
    probs = [0.1, 0.2, 0.8, 0.9]

    auc = compute_auc_roc(labels, probs)
    assert auc == 1.0

    ece = compute_ece(labels, probs)
    assert ece >= 0.0

    items = [
        ManifestItem(
            item_id=f"item_{i}",
            relative_path=f"path_{i}.png",
            label=labels[i],
            identity_id=f"id_{i}",
            dataset_name="TestSet",
            generator_family="Deepfakes" if labels[i] == 1 else "real",
        )
        for i in range(4)
    ]

    metrics = evaluate_predictions(items, probs, dataset_name="TestSet", threshold=0.01)
    assert metrics.auc_roc == 1.0
    assert metrics.f1_score > 0.0
    assert "Deepfakes" in metrics.generator_breakdown


def test_robustness_degradations() -> None:
    from evaluation.deepfake.robustness import (
        apply_gaussian_blur,
        apply_gaussian_noise,
        apply_jpeg_compression,
        apply_rescaling,
    )

    img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)

    jpeg_img = apply_jpeg_compression(img, quality=75)
    assert jpeg_img.shape == (64, 64, 3)

    blur_img = apply_gaussian_blur(img, kernel_size=5)
    assert blur_img.shape == (64, 64, 3)

    noise_img = apply_gaussian_noise(img, sigma=10.0)
    assert noise_img.shape == (64, 64, 3)

    rescale_img = apply_rescaling(img, scale=0.5)
    assert rescale_img.shape == (64, 64, 3)

