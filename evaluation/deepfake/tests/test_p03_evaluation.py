from __future__ import annotations

from pathlib import Path

import numpy as np

from evaluation.deepfake.robustness import transform_image
from evaluation.deepfake.video_metrics import (
    build_video_records,
    fixed_frame_indexes,
    video_level_metrics,
)
from scripts import download_model


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


def test_video_level_metrics_group_frames_before_scoring() -> None:
    rows = [
        {
            "path": "original/001/frame_1.png",
            "label": 0,
            "manipulation": "original",
            "status": "evaluated",
            "score": 0.1,
        },
        {
            "path": "original/001/frame_2.png",
            "label": 0,
            "manipulation": "original",
            "status": "evaluated",
            "score": 0.2,
        },
        {
            "path": "Deepfakes/001_002/frame_1.png",
            "label": 1,
            "manipulation": "Deepfakes",
            "status": "evaluated",
            "score": 0.8,
        },
        {
            "path": "Deepfakes/001_002/frame_2.png",
            "label": 1,
            "manipulation": "Deepfakes",
            "status": "no_face",
            "score": "",
        },
    ]

    results = video_level_metrics(rows, threshold=0.5)

    assert results["mean"]["evaluated_videos"] == 2
    assert results["mean"]["metrics"]["accuracy"] == 1
    assert results["mean"]["metrics_by_manipulation"]["Deepfakes"]["roc_auc"] == 1


def test_no_private_artifact_path_is_part_of_the_repository_contract() -> None:
    module_path = Path(__file__).parents[1]
    assert not (module_path / "results").exists()


def test_checkpoint_download_is_pinned_to_the_approved_immutable_revision() -> None:
    assert download_model.MODEL_REVISION == "db138ed0a70e96b087c155912cc1d306d9a97eec"
    assert download_model.MODEL_REVISION in download_model.MODEL_URL
    assert download_model.EXPECTED_SHA256 == (
        "c5c2002b5ef6c7ee0c542d7d203e16386dc641b685859d8a58ac883b52c8e4c9"
    )
