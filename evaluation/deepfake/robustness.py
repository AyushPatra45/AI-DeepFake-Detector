from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

import cv2
import numpy as np

from evaluation.deepfake.catalog import CatalogRecord, read_catalog

CONDITIONS = (
    "jpeg-q95",
    "jpeg-q75",
    "jpeg-q50",
    "resize-75",
    "resize-50",
    "blur-0.5",
    "blur-1.0",
    "blur-2.0",
    "noise-2",
    "noise-5",
    "noise-10",
)


def _sample_seed(sample_id: str, seed: int) -> int:
    digest = hashlib.sha256(f"{seed}:{sample_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def transform_image(
    image: np.ndarray, *, condition: str, sample_id: str, seed: int = 2205
) -> np.ndarray:
    if condition not in CONDITIONS:
        raise ValueError(f"Unsupported robustness condition: {condition}")
    if condition.startswith("jpeg-q"):
        quality = int(condition.removeprefix("jpeg-q"))
        ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok:
            raise ValueError("JPEG encoding failed")
        transformed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if transformed is None:
            raise ValueError("JPEG decoding failed")
        return transformed
    if condition.startswith("resize-"):
        scale = int(condition.removeprefix("resize-")) / 100
        height, width = image.shape[:2]
        reduced = cv2.resize(
            image,
            (max(1, round(width * scale)), max(1, round(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
        return cv2.resize(reduced, (width, height), interpolation=cv2.INTER_LINEAR)
    if condition.startswith("blur-"):
        sigma = float(condition.removeprefix("blur-"))
        return cv2.GaussianBlur(image, (0, 0), sigmaX=sigma, sigmaY=sigma)

    sigma = float(condition.removeprefix("noise-"))
    generator = np.random.default_rng(_sample_seed(sample_id, seed))
    noise = generator.normal(0.0, sigma, image.shape)
    return np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def _metadata_row(record: CatalogRecord, path: str) -> dict[str, str | int]:
    return {
        "path": path,
        "label": record.label,
        "identity_ids": ";".join(record.identity_ids),
        "source_group": record.source_group,
        "manipulation": record.manipulation,
    }


def generate_condition(
    *, catalog_path: Path, data_root: Path, output_root: Path, condition: str, seed: int
) -> tuple[Path, int]:
    records = read_catalog(catalog_path)
    condition_root = output_root / condition
    metadata_path = output_root / f"{condition}-metadata.csv"
    rows = []
    for record in records:
        source = data_root / Path(record.path)
        image = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if image is None:
            continue
        transformed = transform_image(
            image, condition=condition, sample_id=record.sample_id, seed=seed
        )
        relative_path = Path(record.manipulation) / f"{record.sample_id}.png"
        destination = condition_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(destination), transformed):
            raise OSError(f"Could not write transformed image: {destination}")
        rows.append(_metadata_row(record, relative_path.as_posix()))

    with metadata_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=("path", "label", "identity_ids", "source_group", "manipulation"),
        )
        writer.writeheader()
        writer.writerows(rows)
    return metadata_path, len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate one private deterministic robustness condition from a frozen catalog"
    )
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--condition", required=True, choices=CONDITIONS)
    parser.add_argument("--seed", type=int, default=2205)
    args = parser.parse_args()
    metadata_path, count = generate_condition(
        catalog_path=args.catalog,
        data_root=args.data_root,
        output_root=args.output_root,
        condition=args.condition,
        seed=args.seed,
    )
    print(f"Generated {count} samples; private metadata: {metadata_path}")


if __name__ == "__main__":
    main()
