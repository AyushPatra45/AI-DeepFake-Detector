"""Recover evidence from the project's known-seed shuffled RGB LSB format."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from app.forensics.lsb import MARKER, MAX_EXTRACTED_BYTES

MAX_PIXELS = 4_000_000


def recover(source: Path, *, seed: int, payload_size: int) -> bytes:
    if seed < 0:
        raise ValueError("Seed must be non-negative")
    if not 1 <= payload_size <= MAX_EXTRACTED_BYTES:
        raise ValueError(f"Payload size must be between 1 and {MAX_EXTRACTED_BYTES} bytes")
    with Image.open(source) as image:
        if image.width * image.height > MAX_PIXELS:
            raise ValueError(f"Image exceeds the {MAX_PIXELS:,}-pixel recovery limit")
        flat = np.asarray(image.convert("RGB"), dtype=np.uint8).reshape(-1)

    byte_count = len(MARKER) + payload_size + 1
    if byte_count * 8 > flat.size:
        raise ValueError("Requested payload exceeds image capacity")
    positions = np.random.default_rng(seed).permutation(flat.size)
    decoded = np.packbits(flat[positions[: byte_count * 8]] & 1).tobytes()
    if not decoded.startswith(MARKER) or decoded[-1] != 0:
        raise ValueError("Expected marker or terminator not found; check seed, format and size")
    return decoded[len(MARKER):-1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--payload-size", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path, help="New file for inert bytes")
    args = parser.parse_args()
    try:
        payload = recover(args.source, seed=args.seed, payload_size=args.payload_size)
        with args.output.open("xb") as output:
            output.write(payload)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Recovery failed: {error}\n")
    print(f"Recovered {len(payload)} bytes to {args.output}")


if __name__ == "__main__":
    main()
