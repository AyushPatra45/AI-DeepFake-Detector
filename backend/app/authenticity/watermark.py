from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

MAX_WATERMARK_FRAMES = 12
MAX_WATERMARK_EDGE = 1280


@dataclass(frozen=True)
class VisibleWatermarkResult:
    candidate_detected: bool
    match_score: float
    location: str | None
    bounding_box: tuple[int, int, int, int] | None
    analysed_frames: int
    artifact_path: Path | None


def detect_google_sparkle(
    image_paths: list[Path],
    *,
    artifact_path: Path,
) -> VisibleWatermarkResult:
    indices = np.linspace(
        0, len(image_paths) - 1, min(len(image_paths), MAX_WATERMARK_FRAMES), dtype=int
    )
    contrast_maps = []
    reference = None
    for index in indices:
        image = cv2.imread(str(image_paths[index]))
        if image is None:
            continue
        height, width = image.shape[:2]
        scale = min(1.0, MAX_WATERMARK_EDGE / max(height, width))
        image = cv2.resize(image, (max(1, round(width * scale)), max(1, round(height * scale))))
        if reference is None:
            reference = image
        elif image.shape[:2] != reference.shape[:2]:
            image = cv2.resize(image, (reference.shape[1], reference.shape[0]))
        contrast_maps.append(_local_bright_contrast(image))
    if reference is None:
        return VisibleWatermarkResult(False, 0.0, None, None, 0, None)

    evidence_map = np.median(np.stack(contrast_maps), axis=0).astype(np.uint8)
    score, location, bounding_box = _best_corner_match(evidence_map)
    threshold = 0.60 if len(contrast_maps) >= 3 else 0.88
    detected = score >= threshold and location == "bottom_right"

    saved_artifact = None
    if detected and bounding_box is not None:
        saved_artifact = _write_evidence_overlay(
            reference,
            bounding_box,
            score=score,
            destination=artifact_path,
        )

    return VisibleWatermarkResult(
        candidate_detected=detected,
        match_score=round(score, 6),
        location=location if detected else None,
        bounding_box=bounding_box if detected else None,
        analysed_frames=len(contrast_maps),
        artifact_path=saved_artifact,
    )


def _local_bright_contrast(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    sigma = max(4.0, min(gray.shape) / 60)
    background = cv2.GaussianBlur(gray, (0, 0), sigma)
    positive_contrast = cv2.subtract(gray, background)
    return cv2.normalize(positive_contrast, None, 0, 255, cv2.NORM_MINMAX)


def _sparkle_template(size: int) -> np.ndarray:
    template = np.zeros((size, size), dtype=np.uint8)
    center = size / 2
    outer = size * 0.47
    inner = size * 0.14
    points = np.array(
        [
            (center, center - outer),
            (center + inner, center - inner),
            (center + outer, center),
            (center + inner, center + inner),
            (center, center + outer),
            (center - inner, center + inner),
            (center - outer, center),
            (center - inner, center - inner),
        ],
        dtype=np.int32,
    )
    cv2.fillPoly(template, [points], 255)
    return cv2.GaussianBlur(template, (3, 3), 0)


def _best_corner_match(
    evidence_map: np.ndarray,
) -> tuple[float, str | None, tuple[int, int, int, int] | None]:
    height, width = evidence_map.shape
    regions = {
        "top_left": (0, 0, int(width * 0.35), int(height * 0.45)),
        "top_right": (int(width * 0.65), 0, width, int(height * 0.45)),
        "bottom_left": (0, int(height * 0.55), int(width * 0.35), height),
        "bottom_right": (int(width * 0.65), int(height * 0.55), width, height),
    }
    base_size = max(24, min(96, round(min(height, width) * 0.075)))
    sizes = sorted(
        {
            min(96, max(18, round(base_size * scale)))
            for scale in (0.7, 0.8, 0.9, 1, 1.1, 1.25, 1.5, 1.75, 2)
        }
    )
    template = _sparkle_template(64)
    best_score = 0.0
    best_location = None
    best_box = None

    for location, (x0, y0, x1, y1) in regions.items():
        region = evidence_map[y0:y1, x0:x1]
        for size in sizes:
            if region.shape[0] < size or region.shape[1] < size:
                continue
            resized_template = cv2.resize(template, (size, size), interpolation=cv2.INTER_AREA)
            response = cv2.matchTemplate(region, resized_template, cv2.TM_CCOEFF_NORMED)
            _, score, _, match = cv2.minMaxLoc(response)
            if score > best_score:
                best_score = float(score)
                best_location = location
                best_box = (x0 + match[0], y0 + match[1], size, size)

    return best_score, best_location, best_box


def _write_evidence_overlay(
    image: np.ndarray,
    bounding_box: tuple[int, int, int, int],
    *,
    score: float,
    destination: Path,
) -> Path:
    x, y, width, height = bounding_box
    overlay = image.copy()
    line_width = max(2, round(min(image.shape[:2]) / 300))
    cv2.rectangle(overlay, (x, y), (x + width, y + height), (0, 220, 255), line_width)
    label = f"Visible watermark candidate {score:.2f}"
    text_y = max(24, y - 10)
    (text_width, _), _ = cv2.getTextSize(
        label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2
    )
    text_x = min(max(8, x - 8), max(8, image.shape[1] - text_width - 8))
    cv2.putText(
        overlay,
        label,
        (text_x, text_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 0, 0),
        4,
        cv2.LINE_AA,
    )
    cv2.putText(
        overlay,
        label,
        (text_x, text_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 220, 255),
        2,
        cv2.LINE_AA,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(destination), overlay):
        raise OSError(f"Could not write watermark evidence to {destination}")
    return destination
