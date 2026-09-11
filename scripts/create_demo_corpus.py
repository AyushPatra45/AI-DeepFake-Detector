from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

MARKER = b"STEGv1:"
DEFAULT_PAYLOAD = b"controlled-demo-payload"
DEFAULT_SEED = 20260912
IMAGE_SIZE = (320, 240)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _stabilise_lsb_prefix(image: Image.Image) -> Image.Image:
    pixels = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    flattened = pixels.reshape(-1)
    flattened[:512] &= 0xFE
    return Image.fromarray(pixels, mode="RGB")


def _create_cover(seed: int) -> Image.Image:
    width, height = IMAGE_SIZE
    y, x = np.indices((height, width), dtype=np.uint16)
    rng = np.random.default_rng(seed)
    texture = rng.integers(0, 19, size=(height, width), dtype=np.uint16)
    pixels = np.stack(
        (
            (3 * x + 2 * y + texture) % 256,
            (x + 4 * y + 2 * texture + 47) % 256,
            (5 * x + y + 3 * texture + 91) % 256,
        ),
        axis=2,
    ).astype(np.uint8)
    image = Image.fromarray(pixels, mode="RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((24, 24, 130, 105), fill=(31, 117, 138), outline=(245, 247, 250), width=4)
    draw.ellipse((175, 36, 286, 147), fill=(221, 104, 72), outline=(22, 35, 52), width=5)
    draw.polygon(((58, 196), (139, 127), (210, 207)), fill=(246, 199, 68))
    draw.line((0, 224, 319, 166), fill=(18, 28, 45), width=7)
    return _stabilise_lsb_prefix(image)


def _embed_marker_payload(image: Image.Image, payload: bytes) -> Image.Image:
    if not payload:
        raise ValueError("Payload must not be empty")
    if b"\x00" in payload:
        raise ValueError("Payload cannot contain the NUL terminator byte")

    pixels = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    encoded = MARKER + payload + b"\x00"
    bits = np.unpackbits(np.frombuffer(encoded, dtype=np.uint8), bitorder="big")
    flattened = pixels.reshape(-1)
    if len(bits) > len(flattened):
        raise ValueError("Payload is too large for the generated cover image")
    flattened[: len(bits)] = (flattened[: len(bits)] & 0xFE) | bits
    return Image.fromarray(pixels, mode="RGB")


def _create_screenshot_style_image(cover: Image.Image) -> Image.Image:
    image = Image.new("RGB", IMAGE_SIZE, color=(238, 242, 246))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 319, 27), fill=(28, 39, 54))
    draw.rectangle((0, 28, 57, 239), fill=(37, 63, 70))
    draw.rectangle((73, 45, 303, 216), fill=(255, 255, 255), outline=(173, 185, 196), width=2)
    preview = cover.resize((196, 112))
    image.paste(preview, (90, 64))
    draw.rectangle((90, 187, 170, 201), fill=(15, 137, 151))
    draw.rectangle((180, 187, 286, 201), fill=(210, 217, 224))
    return _stabilise_lsb_prefix(image)


def _sample(
    path: Path,
    *,
    scenario: str,
    supported_lsb_payload: bool,
    ela_use: str,
) -> dict[str, object]:
    with Image.open(path) as image:
        width, height = image.size
        media_format = image.format
    return {
        "file": path.name,
        "sha256": _sha256(path),
        "format": media_format,
        "width": width,
        "height": height,
        "scenario": scenario,
        "expected": {
            "supported_lsb_payload": supported_lsb_payload,
            "ela_use": ela_use,
        },
    }


def generate_corpus(
    output_dir: Path,
    *,
    payload: bytes = DEFAULT_PAYLOAD,
    seed: int = DEFAULT_SEED,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cover = _create_cover(seed)

    clean_path = output_dir / "clean-cover.png"
    stego_path = output_dir / "lsb-marker-payload.png"
    original_path = output_dir / "original-quality-95.jpg"
    recompressed_path = output_dir / "recompressed-quality-55.jpg"
    edited_path = output_dir / "edited-region-quality-88.jpg"
    screenshot_path = output_dir / "screenshot-style.png"

    cover.save(clean_path, format="PNG", compress_level=9)
    _embed_marker_payload(cover, payload).save(stego_path, format="PNG", compress_level=9)
    cover.save(
        original_path,
        format="JPEG",
        quality=95,
        subsampling=0,
        optimize=False,
        progressive=False,
    )

    with Image.open(original_path) as source:
        decoded_original = source.convert("RGB")
    decoded_original.save(
        recompressed_path,
        format="JPEG",
        quality=55,
        subsampling=0,
        optimize=False,
        progressive=False,
    )

    edited = decoded_original.copy()
    edited_region = decoded_original.crop((24, 48, 124, 148)).transpose(
        Image.Transpose.FLIP_LEFT_RIGHT
    )
    edited.paste(edited_region, (188, 72))
    ImageDraw.Draw(edited).rectangle((186, 70, 290, 174), outline=(248, 247, 242), width=2)
    edited.save(
        edited_path,
        format="JPEG",
        quality=88,
        subsampling=0,
        optimize=False,
        progressive=False,
    )
    _create_screenshot_style_image(cover).save(
        screenshot_path,
        format="PNG",
        compress_level=9,
    )

    samples = [
        _sample(
            clean_path,
            scenario="Synthetic PNG cover without an embedded payload",
            supported_lsb_payload=False,
            ela_use="PNG baseline; ELA output is not authenticity proof",
        ),
        _sample(
            stego_path,
            scenario="Same cover with a documented STEGv1 LSB marker payload",
            supported_lsb_payload=True,
            ela_use="LSB extraction case; ELA is not expected to expose the payload",
        ),
        _sample(
            original_path,
            scenario="Synthetic image encoded once at JPEG quality 95",
            supported_lsb_payload=False,
            ela_use="Reference JPEG compression case",
        ),
        _sample(
            recompressed_path,
            scenario="Quality-95 JPEG decoded and recompressed at quality 55",
            supported_lsb_payload=False,
            ela_use="Controlled recompression case",
        ),
        _sample(
            edited_path,
            scenario="Mirrored rectangular region inserted before JPEG quality-88 encoding",
            supported_lsb_payload=False,
            ela_use="Controlled visible edit; compare its heatmap with both JPEG references",
        ),
        _sample(
            screenshot_path,
            scenario="Synthetic screenshot-style PNG with flat interface regions",
            supported_lsb_payload=False,
            ela_use="Screenshot/PNG false-positive discussion case",
        ),
    ]
    manifest: dict[str, object] = {
        "schema_version": 1,
        "generator": "scripts/create_demo_corpus.py",
        "generator_seed": seed,
        "purpose": "Safe, reproducible demonstration of ELA and supported LSB extraction",
        "restrictions": [
            "Not a deepfake training or accuracy dataset",
            "Not evidence of real-world detector generalisation",
            "ELA and LSB statistics are indicators, not authenticity proof",
        ],
        "licensing": "Project-generated synthetic media; no third-party source media",
        "payload": {
            "encoding": "UTF-8 text terminated by NUL",
            "marker": MARKER.decode("ascii"),
            "value": payload.decode("utf-8"),
            "embedding_order": "Interleaved RGB channel LSBs, row-major pixel order",
            "bit_plane": 0,
        },
        "samples": samples,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a deterministic, licence-safe image-forensics demonstration corpus"
    )
    parser.add_argument("--output-dir", type=Path, default=Path("demo/generated"))
    parser.add_argument("--payload", default=DEFAULT_PAYLOAD.decode("ascii"))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    manifest = generate_corpus(
        args.output_dir,
        payload=args.payload.encode("utf-8"),
        seed=args.seed,
    )
    print(f"Generated {len(manifest['samples'])} samples in {args.output_dir}")
    print(f"Manifest: {args.output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
