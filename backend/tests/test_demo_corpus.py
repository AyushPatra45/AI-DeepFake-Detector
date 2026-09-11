from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.forensics.ela import generate_ela
from app.forensics.lsb import analyse_lsb

from scripts.create_demo_corpus import DEFAULT_PAYLOAD, generate_corpus


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_demo_corpus_is_reproducible_and_manifested(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    first_manifest = generate_corpus(first_dir)
    second_manifest = generate_corpus(second_dir)

    assert first_manifest == second_manifest
    assert len(first_manifest["samples"]) == 6
    assert (first_dir / "manifest.json").read_bytes() == (second_dir / "manifest.json").read_bytes()

    saved_manifest = json.loads((first_dir / "manifest.json").read_text(encoding="utf-8"))
    for sample in saved_manifest["samples"]:
        sample_path = first_dir / sample["file"]
        assert sample_path.exists()
        assert sample["sha256"] == _sha256(sample_path)


def test_demo_corpus_contains_expected_lsb_control_cases(tmp_path: Path) -> None:
    output_dir = tmp_path / "demo"
    generate_corpus(output_dir)

    clean_result = analyse_lsb(output_dir / "clean-cover.png")
    stego_result = analyse_lsb(output_dir / "lsb-marker-payload.png")

    assert clean_result.findings["supported_payload_detected"] is False
    assert clean_result.extracted_payload is None
    assert stego_result.findings["supported_payload_detected"] is True
    assert stego_result.findings["extraction_method"] == "STEGv1 marker"
    assert stego_result.extracted_payload == DEFAULT_PAYLOAD


def test_demo_corpus_ela_cases_generate_measured_heatmaps(tmp_path: Path) -> None:
    output_dir = tmp_path / "demo"
    heatmap_dir = tmp_path / "heatmaps"
    generate_corpus(output_dir)

    results = {
        name: generate_ela(output_dir / name, heatmap_dir / f"{Path(name).stem}.png")
        for name in (
            "original-quality-95.jpg",
            "recompressed-quality-55.jpg",
            "edited-region-quality-88.jpg",
            "screenshot-style.png",
        )
    }

    assert all(result.output_path.exists() for result in results.values())
    assert all(result.max_error >= 0 for result in results.values())
    assert all(0 <= result.highlighted_pixel_ratio <= 1 for result in results.values())
