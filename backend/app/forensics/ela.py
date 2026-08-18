from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageEnhance


@dataclass(frozen=True)
class ElaResult:
    output_path: Path
    jpeg_quality: int
    mean_error: float
    percentile_95_error: float
    max_error: int
    highlighted_pixel_ratio: float


def generate_ela(
    source_path: Path,
    output_path: Path,
    *,
    jpeg_quality: int = 90,
    highlight_threshold: int = 20,
) -> ElaResult:
    if not 1 <= jpeg_quality <= 100:
        raise ValueError("JPEG quality must be between 1 and 100")

    with Image.open(source_path) as source:
        original = source.convert("RGB")

    recompressed_bytes = BytesIO()
    original.save(recompressed_bytes, format="JPEG", quality=jpeg_quality)
    recompressed_bytes.seek(0)
    with Image.open(recompressed_bytes) as encoded:
        recompressed = encoded.convert("RGB")

    difference = ImageChops.difference(original, recompressed)
    difference_array = np.asarray(difference, dtype=np.uint8)
    per_pixel_error = difference_array.max(axis=2)
    max_error = int(per_pixel_error.max())
    scale = 255.0 / max(max_error, 1)
    visual = ImageEnhance.Brightness(difference).enhance(scale)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    visual.save(output_path, format="PNG")
    return ElaResult(
        output_path=output_path,
        jpeg_quality=jpeg_quality,
        mean_error=round(float(per_pixel_error.mean()), 4),
        percentile_95_error=round(float(np.percentile(per_pixel_error, 95)), 4),
        max_error=max_error,
        highlighted_pixel_ratio=round(float(np.mean(per_pixel_error >= highlight_threshold)), 6),
    )
