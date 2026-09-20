from __future__ import annotations

from pathlib import Path

import numpy as np

from evaluation.deepfake.robustness import transform_image
from evaluation.deepfake.video_metrics import build_video_records, fixed_frame_indexes


def test_fixed_frame_indexes_are_five_deterministic_interior_positions() -> None:
    assert fixed_frame_indexes(60) == (10, 20, 30, 40, 50)
    assert fixed_frame_indexes(5) == (0, 1, 2, 3, 4)


def test_official_pair_expands_to_approved_video_families() -> None:
    pairs = [(f"{index:03d}", f"{index + 70:03d}") for index in range(70)]
    records = build_video_records(pairs)

    assert len(records) == 700
    assert sum(record.label == "real" for record in records) == 140
    assert sum(record.manipulation == "Deepfakes" for record in records) == 140
    assert {record.manipulation for record in records} == {
        "original",
        "Deepfakes",
        "Face2Face",
        "FaceSwap",
        "NeuralTextures",
    }
    assert all("c23/videos" in record.relative_path for record in records)


def test_gaussian_noise_is_reproducible_and_sample_specific() -> None:
    image = np.full((8, 8, 3), 127, dtype=np.uint8)
    first = transform_image(image, condition="noise-5", sample_id="a", seed=2205)
    repeated = transform_image(image, condition="noise-5", sample_id="a", seed=2205)
    other = transform_image(image, condition="noise-5", sample_id="b", seed=2205)

    assert np.array_equal(first, repeated)
    assert not np.array_equal(first, other)


def test_resize_degradation_preserves_image_shape() -> None:
    image = np.arange(12 * 16 * 3, dtype=np.uint8).reshape((12, 16, 3))
    transformed = transform_image(image, condition="resize-50", sample_id="sample")

    assert transformed.shape == image.shape


def test_no_private_artifact_path_is_part_of_the_repository_contract() -> None:
    module_path = Path(__file__).parents[1]
    assert not (module_path / "results").exists()
