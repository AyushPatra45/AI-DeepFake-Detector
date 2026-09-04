from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import platform
import subprocess
from pathlib import Path

import cv2
from app.deepfake.face import FaceCropper
from app.deepfake.runtime import ModelRuntime, load_runtime

from evaluation.catalog import CatalogRecord, read_catalog, sha256_file
from evaluation.metrics import binary_metrics

PREDICTION_FIELDS = (
    "sample_id",
    "path",
    "label",
    "score",
    "prediction",
    "status",
    "dataset",
    "manipulation",
    "source_group",
)


def _git_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _safe_media_path(data_root: Path, relative_value: str) -> Path:
    relative_path = Path(relative_value)
    if relative_path.is_absolute():
        raise ValueError(f"Manifest path must be relative: {relative_value!r}")
    data_root = data_root.resolve()
    media_path = (data_root / relative_path).resolve()
    try:
        media_path.relative_to(data_root)
    except ValueError as error:
        raise ValueError(f"Manifest path escapes the data root: {relative_value!r}") from error
    return media_path


def _predict_records(
    records: list[CatalogRecord],
    *,
    data_root: Path,
    runtime: ModelRuntime,
    image_size: int,
    batch_size: int,
    threshold: float,
) -> list[dict[str, object]]:
    cropper = FaceCropper(target_size=image_size)
    rows: list[dict[str, object]] = []
    pending_faces = []
    pending_indexes: list[int] = []

    def flush() -> None:
        if not pending_faces:
            return
        scores = runtime.predict(pending_faces, batch_size=batch_size)
        for row_index, score in zip(pending_indexes, scores, strict=True):
            rows[row_index]["score"] = round(score, 8)
            rows[row_index]["prediction"] = int(score >= threshold)
            rows[row_index]["status"] = "evaluated"
        pending_faces.clear()
        pending_indexes.clear()

    for record in records:
        row: dict[str, object] = {
            "sample_id": record.sample_id,
            "path": record.path,
            "label": record.label,
            "score": "",
            "prediction": "",
            "status": "read_error",
            "dataset": record.dataset,
            "manipulation": record.manipulation,
            "source_group": record.source_group,
        }
        rows.append(row)
        image = cv2.imread(str(_safe_media_path(data_root, record.path)), cv2.IMREAD_COLOR)
        if image is None:
            continue
        face = cropper.crop_largest(image)
        if face is None:
            row["status"] = "no_face"
            continue
        pending_faces.append(face)
        pending_indexes.append(len(rows) - 1)
        if len(pending_faces) >= batch_size:
            flush()
    flush()
    return rows


def evaluate_manifest(
    *,
    manifest_path: Path,
    data_root: Path,
    checkpoint_path: Path,
    output_dir: Path,
    image_size: int = 512,
    batch_size: int = 4,
    threshold_override: float | None = None,
) -> dict[str, object]:
    if image_size <= 0 or batch_size <= 0:
        raise ValueError("image_size and batch_size must be positive")
    records = read_catalog(manifest_path)
    runtime = load_runtime(checkpoint_path)
    threshold = runtime.threshold if threshold_override is None else threshold_override
    rows = _predict_records(
        records,
        data_root=data_root,
        runtime=runtime,
        image_size=image_size,
        batch_size=batch_size,
        threshold=threshold,
    )
    evaluated = [row for row in rows if row["status"] == "evaluated"]
    if not evaluated:
        raise ValueError("No samples could be evaluated; check paths and face detection")
    labels = [int(row["label"]) for row in evaluated]
    scores = [float(row["score"]) for row in evaluated]
    results: dict[str, object] = {
        "model": {
            "name": "dual-stream-0.1.0",
            "checkpoint_sha256": runtime.checkpoint_sha256,
            "checkpoint_threshold": runtime.threshold,
            "evaluation_threshold": threshold,
            "calibration_temperature": runtime.temperature,
        },
        "dataset": {
            "manifest": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "catalog_samples": len(records),
            "evaluated_samples": len(evaluated),
            "no_face_samples": sum(row["status"] == "no_face" for row in rows),
            "read_errors": sum(row["status"] == "read_error" for row in rows),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "git_revision": _git_revision(),
            "packages": {
                package: _package_version(package)
                for package in ("numpy", "opencv-python-headless", "torch", "torchvision")
            },
        },
        "metrics": binary_metrics(labels, scores, threshold=threshold),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "predictions.csv").open(
        "w", newline="", encoding="utf-8"
    ) as predictions_file:
        writer = csv.DictWriter(predictions_file, fieldnames=PREDICTION_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / "metrics.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    confusion = results["metrics"]["confusion_matrix"]
    with (output_dir / "confusion_matrix.csv").open(
        "w", newline="", encoding="utf-8"
    ) as confusion_file:
        writer = csv.writer(confusion_file)
        writer.writerow(["actual/predicted", "real", "fake"])
        writer.writerow(["real", confusion["true_negative"], confusion["false_positive"]])
        writer.writerow(["fake", confusion["false_negative"], confusion["true_positive"]])
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the attributed dual-stream checkpoint on a fixed manifest"
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument(
        "--checkpoint", type=Path, default=Path("models/dual_stream_calibrated.pth")
    )
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation/results/baseline"))
    parser.add_argument("--image-size", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--threshold", type=float)
    args = parser.parse_args()

    results = evaluate_manifest(
        manifest_path=args.manifest,
        data_root=args.data_root,
        checkpoint_path=args.checkpoint,
        output_dir=args.output_dir,
        image_size=args.image_size,
        batch_size=args.batch_size,
        threshold_override=args.threshold,
    )
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
