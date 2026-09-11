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
from app.deepfake.runtime import ModelRuntime, load_runtime
from app.schemas import Artifact, FrameFinding, MediaInfo, MediaType, ModuleStatus


class _BatchRecordingModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.batch_sizes: list[int] = []

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        self.batch_sizes.append(inputs.shape[0])
        return inputs[:, :1, 0, 0]


class _StubRuntime:
    threshold = 0.5
    temperature = 1.25
    checkpoint_sha256 = "test-checkpoint-sha256"

    def __init__(self, probabilities: list[float]) -> None:
        self.probabilities = probabilities
        self.calls: list[tuple[int, int]] = []

    def predict(self, faces_rgb: list[np.ndarray], *, batch_size: int = 4) -> list[float]:
        self.calls.append((len(faces_rgb), batch_size))
        return self.probabilities


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


def test_runtime_predict_preserves_order_across_batches() -> None:
    model = _BatchRecordingModel()
    runtime = ModelRuntime(
        model=model,
        device=torch.device("cpu"),
        threshold=0.5,
        temperature=2.0,
        checkpoint_sha256="test-checkpoint-sha256",
    )
    pixel_values = [0, 64, 128, 192, 255]
    faces = [np.full((2, 2, 3), value, dtype=np.uint8) for value in pixel_values]

    probabilities = runtime.predict(faces, batch_size=2)

    expected = torch.sigmoid(torch.tensor(pixel_values, dtype=torch.float32) / 255 / 2).tolist()
    assert probabilities == pytest.approx(expected)
    assert model.batch_sizes == [2, 2, 1]


def test_runtime_predict_accepts_an_empty_face_list_without_running_model() -> None:
    model = _BatchRecordingModel()
    runtime = ModelRuntime(
        model=model,
        device=torch.device("cpu"),
        threshold=0.5,
        temperature=1.0,
        checkpoint_sha256="test-checkpoint-sha256",
    )

    assert runtime.predict([], batch_size=2) == []
    assert model.batch_sizes == []


def test_load_runtime_rejects_an_unsupported_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint = tmp_path / "invalid.pth"
    checkpoint.write_bytes(b"placeholder")
    monkeypatch.setattr("app.deepfake.runtime.torch.load", lambda *args, **kwargs: [])

    with pytest.raises(ValueError, match="Unsupported checkpoint structure"):
        load_runtime(checkpoint)


def test_unreadable_image_is_skipped_without_inference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint = tmp_path / "model.pth"
    checkpoint.write_bytes(b"placeholder")
    source = tmp_path / "unreadable.png"
    source.write_bytes(b"not an image")
    runtime = _StubRuntime([0.9])
    analyzer = DeepfakeAnalyzer(checkpoint_path=checkpoint)
    analyzer._runtime = runtime
    context = AnalysisContext(
        job_id="job-unreadable",
        source_path=source,
        artifact_dir=tmp_path / "artifacts",
        media=MediaInfo(media_type=MediaType.PNG, width=10, height=10),
        frames=[],
    )
    monkeypatch.setattr("app.deepfake.adapter.cv2.imread", lambda *args, **kwargs: None)

    result = analyzer.analyse(context)

    assert result.status == ModuleStatus.SKIPPED
    assert result.warnings == ["No detectable face was available for the face-focused model"]
    assert runtime.calls == []
    assert not context.artifact_dir.exists()


def test_video_analysis_scores_all_faces_and_preserves_frame_association(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint = tmp_path / "model.pth"
    checkpoint.write_bytes(b"placeholder")
    frames = [
        FrameFinding(
            frame_index=index,
            timestamp_seconds=index / 2,
            artifact=Artifact(
                kind="sampled_frame",
                path=f"/artifacts/job-video/frame-{index:04d}.jpg",
            ),
        )
        for index in range(5)
    ]
    context = AnalysisContext(
        job_id="job-video",
        source_path=tmp_path / "video.mp4",
        artifact_dir=tmp_path / "job-video",
        media=MediaInfo(media_type=MediaType.MP4, width=100, height=100),
        frames=frames,
    )
    probabilities = [0.1, 0.6, 0.9, 0.2, 0.7]
    runtime = _StubRuntime(probabilities)
    analyzer = DeepfakeAnalyzer(checkpoint_path=checkpoint, image_size=32, batch_size=2)
    analyzer._runtime = runtime
    face = np.full((32, 32, 3), 128, dtype=np.uint8)
    monkeypatch.setattr("app.deepfake.adapter.cv2.imread", lambda *args, **kwargs: face)
    monkeypatch.setattr(FaceCropper, "crop_largest", lambda *args, **kwargs: face)
    monkeypatch.setattr("app.deepfake.adapter.save_diagnostics", lambda *args, **kwargs: [])

    result = analyzer.analyse(context)

    expected_score = softmax_weighted_score(probabilities, temperature=0.1)
    assert result.status == ModuleStatus.COMPLETED
    assert runtime.calls == [(5, 2)]
    assert [frame.deepfake_probability for frame in frames] == probabilities
    assert result.findings["deepfake_probability"] == round(expected_score, 6)
    assert result.findings["decision"] == "suspicious"
    assert result.findings["analysed_faces"] == 5
    assert result.findings["candidate_frames"] == 5
    assert [item["frame_index"] for item in result.findings["frame_scores"]] == list(range(5))
    assert result.settings["checkpoint_sha256"] == runtime.checkpoint_sha256
