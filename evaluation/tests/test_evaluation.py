from __future__ import annotations

import csv
from pathlib import Path

import pytest

from evaluation.catalog import CatalogRecord, build_catalog, write_catalog
from evaluation.metrics import binary_metrics, roc_auc
from evaluation.splitting import audit_split_integrity, split_catalog


def _record(
    sample: str,
    label: int,
    identity: str,
    group: str,
    checksum: str,
) -> CatalogRecord:
    return CatalogRecord(
        sample_id=sample,
        path=f"{sample}.jpg",
        label=label,
        identity_ids=tuple(identity.split(";")),
        source_group=group,
        dataset="controlled",
        manipulation="original" if label == 0 else "test-fake",
        sha256=checksum,
    )


def test_split_is_deterministic_and_identity_disjoint() -> None:
    records = [
        _record("a-real", 0, "a", "video-a", "hash-a"),
        _record("a-fake", 1, "a;b", "video-ab", "hash-ab"),
        _record("b-real", 0, "b", "video-b", "hash-b"),
        _record("c-real", 0, "c", "video-c", "hash-c"),
        _record("c-fake", 1, "c;d", "video-cd", "hash-cd"),
        _record("d-real", 0, "d", "video-d", "hash-d"),
        _record("e-real", 0, "e", "video-e", "hash-e"),
        _record("e-fake", 1, "e;f", "video-ef", "hash-ef"),
        _record("f-real", 0, "f", "video-f", "hash-f"),
    ]

    first = split_catalog(records, seed=2205)
    second = split_catalog(records, seed=2205)

    assert {
        split: [record.sample_id for record in assigned]
        for split, assigned in first.assignments.items()
    } == {
        split: [record.sample_id for record in assigned]
        for split, assigned in second.assignments.items()
    }
    assert all(first.assignments.values())
    audit_split_integrity(first.assignments)


def test_audit_rejects_identity_leakage() -> None:
    assignments = {
        "train": [_record("train", 0, "same-person", "one", "one")],
        "validation": [],
        "test": [_record("test", 1, "same-person;other", "two", "two")],
    }
    with pytest.raises(ValueError, match="Leakage detected"):
        audit_split_integrity(assignments)


def test_metrics_include_auc_calibration_and_confusion_matrix() -> None:
    metrics = binary_metrics([0, 0, 1, 1], [0.1, 0.4, 0.6, 0.9], threshold=0.5)

    assert metrics["accuracy"] == 1
    assert metrics["f1"] == 1
    assert metrics["roc_auc"] == 1
    assert metrics["confusion_matrix"] == {
        "true_negative": 2,
        "false_positive": 0,
        "false_negative": 0,
        "true_positive": 2,
    }
    assert roc_auc([0, 1], [0.5, 0.5]) == 0.5


def test_catalog_rejects_path_outside_dataset_root(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    metadata = tmp_path / "metadata.csv"
    with metadata.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=["path", "label", "identity_ids", "source_group"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "path": "../outside.jpg",
                "label": "real",
                "identity_ids": "person-1",
                "source_group": "video-1",
            }
        )

    with pytest.raises(ValueError, match="escapes the dataset root"):
        build_catalog(source_root=tmp_path / "data", metadata_path=metadata, dataset="test")


def test_catalog_hashes_and_round_trips_valid_metadata(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    image_path = data_root / "real" / "frame.jpg"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"controlled-test-image")
    metadata = tmp_path / "metadata.csv"
    with metadata.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "path",
                "label",
                "identity_ids",
                "source_group",
                "manipulation",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "path": "real/frame.jpg",
                "label": "real",
                "identity_ids": "person-1",
                "source_group": "video-1",
                "manipulation": "original",
            }
        )

    records = build_catalog(
        source_root=data_root,
        metadata_path=metadata,
        dataset="controlled",
    )
    catalog_path = tmp_path / "catalog.csv"
    write_catalog(records, catalog_path)

    assert records[0].path == "real/frame.jpg"
    assert records[0].label == 0
    assert len(records[0].sha256) == 64
    assert "controlled" in catalog_path.read_text(encoding="utf-8")
