from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from evaluation.deepfake import evaluate as evaluator
from evaluation.deepfake.catalog import CatalogRecord, write_catalog


def _record(sample: str, label: int) -> CatalogRecord:
    return CatalogRecord(
        sample_id=sample,
        path=f"{sample}.jpg",
        label=label,
        identity_ids=(f"identity-{sample}",),
        source_group=f"source-{sample}",
        dataset="controlled",
        manipulation="original" if label == 0 else "test-fake",
        sha256=f"hash-{sample}",
    )


class _FakeRuntime:
    threshold = 0.5
    temperature = 1.25
    checkpoint_sha256 = "checkpoint-sha256"

    def __init__(self, scores: list[float]) -> None:
        self.scores = iter(scores)
        self.batch_lengths: list[int] = []
        self.requested_batch_sizes: list[int] = []

    def predict(self, faces_rgb: list[np.ndarray], *, batch_size: int = 4) -> list[float]:
        self.batch_lengths.append(len(faces_rgb))
        self.requested_batch_sizes.append(batch_size)
        return [next(self.scores) for _ in faces_rgb]


class _FakeCropper:
    target_sizes: list[int] = []

    def __init__(self, *, target_size: int) -> None:
        self.target_sizes.append(target_size)

    def crop_largest(self, image_bgr: np.ndarray) -> np.ndarray | None:
        if not image_bgr.any():
            return None
        return image_bgr


def _install_fakes(
    monkeypatch: pytest.MonkeyPatch,
    runtime: _FakeRuntime,
    *, missing_names: set[str] | None = None,
    no_face_names: set[str] | None = None,
) -> None:
    missing_names = missing_names or set()
    no_face_names = no_face_names or set()

    def fake_imread(path: str, _mode: int) -> np.ndarray | None:
        name = Path(path).stem
        if name in missing_names:
            return None
        value = 0 if name in no_face_names else 1
        return np.full((2, 2, 3), value, dtype=np.uint8)

    monkeypatch.setattr(evaluator, "load_runtime", lambda _path: runtime)
    monkeypatch.setattr(evaluator, "FaceCropper", _FakeCropper)
    monkeypatch.setattr(evaluator.cv2, "imread", fake_imread)
    monkeypatch.setattr(evaluator, "_git_revision", lambda: "test-revision")


def test_evaluate_manifest_batches_records_and_writes_auditable_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "test.csv"
    write_catalog(
        [
            _record("real", 0),
            _record("fake", 1),
            _record("missing", 0),
            _record("no-face", 1),
            _record("extra-fake", 1),
        ],
        manifest,
    )
    runtime = _FakeRuntime([0.1, 0.9, 0.8])
    _FakeCropper.target_sizes.clear()
    _install_fakes(
        monkeypatch,
        runtime,
        missing_names={"missing"},
        no_face_names={"no-face"},
    )
    output_dir = tmp_path / "results"

    results = evaluator.evaluate_manifest(
        manifest_path=manifest,
        data_root=tmp_path / "data",
        checkpoint_path=tmp_path / "checkpoint.pth",
        output_dir=output_dir,
        image_size=224,
        batch_size=2,
    )

    assert runtime.batch_lengths == [2, 1]
    assert runtime.requested_batch_sizes == [2, 2]
    assert _FakeCropper.target_sizes == [224]
    assert results["model"] == {
        "name": "dual-stream-0.1.0",
        "checkpoint_sha256": "checkpoint-sha256",
        "checkpoint_threshold": 0.5,
        "evaluation_threshold": 0.5,
        "calibration_temperature": 1.25,
    }
    assert results["dataset"]["catalog_samples"] == 5
    assert results["dataset"]["evaluated_samples"] == 3
    assert results["dataset"]["no_face_samples"] == 1
    assert results["dataset"]["read_errors"] == 1
    assert results["environment"]["git_revision"] == "test-revision"
    assert results["metrics"]["accuracy"] == 1

    with (output_dir / "predictions.csv").open(newline="", encoding="utf-8") as source:
        predictions = list(csv.DictReader(source))
    assert [row["status"] for row in predictions] == [
        "evaluated",
        "evaluated",
        "read_error",
        "no_face",
        "evaluated",
    ]
    assert predictions[2]["score"] == ""
    assert predictions[3]["prediction"] == ""
    assert json.loads((output_dir / "metrics.json").read_text(encoding="utf-8")) == results
    assert (output_dir / "confusion_matrix.csv").read_text(encoding="utf-8").splitlines() == [
        "actual/predicted,real,fake",
        "real,1,0",
        "fake,0,2",
    ]


def test_evaluate_manifest_rejects_run_when_every_sample_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "test.csv"
    write_catalog([_record("missing", 0), _record("no-face", 1)], manifest)
    runtime = _FakeRuntime([])
    _install_fakes(
        monkeypatch,
        runtime,
        missing_names={"missing"},
        no_face_names={"no-face"},
    )
    output_dir = tmp_path / "results"

    with pytest.raises(ValueError, match="No samples could be evaluated"):
        evaluator.evaluate_manifest(
            manifest_path=manifest,
            data_root=tmp_path / "data",
            checkpoint_path=tmp_path / "checkpoint.pth",
            output_dir=output_dir,
        )

    assert runtime.batch_lengths == []
    assert not output_dir.exists()


@pytest.mark.parametrize("threshold", [-0.01, 1.01])
def test_evaluate_manifest_rejects_invalid_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    threshold: float,
) -> None:
    manifest = tmp_path / "test.csv"
    write_catalog([_record("sample", 0)], manifest)
    _install_fakes(monkeypatch, _FakeRuntime([0.2]))
    output_dir = tmp_path / "results"

    with pytest.raises(ValueError, match="Threshold must be between 0 and 1"):
        evaluator.evaluate_manifest(
            manifest_path=manifest,
            data_root=tmp_path / "data",
            checkpoint_path=tmp_path / "checkpoint.pth",
            output_dir=output_dir,
            threshold_override=threshold,
        )

    assert not output_dir.exists()


@pytest.mark.parametrize(("image_size", "batch_size"), [(0, 1), (1, 0), (-1, 1), (1, -1)])
def test_evaluate_manifest_rejects_non_positive_sizes(
    tmp_path: Path,
    image_size: int,
    batch_size: int,
) -> None:
    with pytest.raises(ValueError, match="image_size and batch_size must be positive"):
        evaluator.evaluate_manifest(
            manifest_path=tmp_path / "unused.csv",
            data_root=tmp_path,
            checkpoint_path=tmp_path / "unused.pth",
            output_dir=tmp_path / "results",
            image_size=image_size,
            batch_size=batch_size,
        )


@pytest.mark.parametrize("unsafe_path", ["../outside.jpg", str(Path("C:/outside.jpg"))])
def test_evaluate_manifest_rejects_unsafe_manifest_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsafe_path: str,
) -> None:
    record = _record("unsafe", 0)
    record = CatalogRecord(**{**record.__dict__, "path": unsafe_path})
    manifest = tmp_path / "test.csv"
    write_catalog([record], manifest)
    _install_fakes(monkeypatch, _FakeRuntime([0.2]))

    with pytest.raises(ValueError, match="Manifest path (must be relative|escapes the data root)"):
        evaluator.evaluate_manifest(
            manifest_path=manifest,
            data_root=tmp_path / "data",
            checkpoint_path=tmp_path / "checkpoint.pth",
            output_dir=tmp_path / "results",
        )
