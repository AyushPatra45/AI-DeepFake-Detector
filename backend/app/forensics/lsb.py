from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

MAX_EXTRACTED_BYTES = 64 * 1024
MARKER = b"STEGv1:"
KNOWN_SIGNATURES = {
    b"%PDF": "PDF",
    b"PK\x03\x04": "ZIP",
    b"\x89PNG\r\n\x1a\n": "PNG",
    b"MZ": "Windows executable",
}


@dataclass(frozen=True)
class LsbResult:
    findings: dict
    extracted_payload: bytes | None


def _entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def _pair_imbalance(channel: np.ndarray) -> float:
    histogram = np.bincount(channel.reshape(-1), minlength=256).astype(np.float64)
    pairs = histogram.reshape(128, 2)
    totals = pairs.sum(axis=1)
    valid = totals > 0
    imbalance = np.abs(pairs[:, 0] - pairs[:, 1]) / np.maximum(totals, 1)
    return round(float(imbalance[valid].mean()) if np.any(valid) else 0.0, 6)


def _decode_supported_payload(bitstream: bytes) -> tuple[bytes | None, str | None]:
    marker_index = bitstream.find(MARKER, 0, 64)
    if marker_index >= 0:
        start = marker_index + len(MARKER)
        end = bitstream.find(b"\x00", start, start + MAX_EXTRACTED_BYTES)
        if end < 0:
            end = min(start + MAX_EXTRACTED_BYTES, len(bitstream))
        payload = bitstream[start:end]
        return (payload or None), "STEGv1 marker"

    if len(bitstream) >= 8:
        declared_length = int.from_bytes(bitstream[:4], "big")
        if 0 < declared_length <= min(MAX_EXTRACTED_BYTES, len(bitstream) - 4):
            payload = bitstream[4 : 4 + declared_length]
            printable_ratio = sum(32 <= byte <= 126 or byte in b"\r\n\t" for byte in payload) / len(
                payload
            )
            signature = next(
                (name for magic, name in KNOWN_SIGNATURES.items() if payload.startswith(magic)),
                None,
            )
            if signature or printable_ratio >= 0.8:
                return payload, f"32-bit length prefix ({signature or 'text-like payload'})"

    signature = next(
        (name for magic, name in KNOWN_SIGNATURES.items() if bitstream.startswith(magic)),
        None,
    )
    if signature:
        return bitstream[:MAX_EXTRACTED_BYTES], f"{signature} signature at LSB stream start"
    return None, None


def analyse_lsb(source_path: Path) -> LsbResult:
    with Image.open(source_path) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)

    channel_names = ("red", "green", "blue")
    channel_findings = {}
    for index, name in enumerate(channel_names):
        channel = rgb[:, :, index]
        bits = channel & 1
        channel_findings[name] = {
            "ones_ratio": round(float(bits.mean()), 6),
            "pair_imbalance": _pair_imbalance(channel),
        }

    interleaved_bits = (rgb.reshape(-1) & 1).astype(np.uint8)
    bitstream = np.packbits(interleaved_bits, bitorder="big").tobytes()
    payload, extraction_method = _decode_supported_payload(bitstream)
    preview_bytes = payload[:160] if payload else b""
    ascii_preview = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in preview_bytes)

    findings = {
        "inspected_bit_plane": 0,
        "available_lsb_bits": int(interleaved_bits.size),
        "channel_statistics": channel_findings,
        "packed_stream_entropy": round(_entropy(bitstream[:MAX_EXTRACTED_BYTES]), 6),
        "supported_payload_detected": payload is not None,
        "extraction_method": extraction_method,
        "extracted_size_bytes": len(payload) if payload else 0,
        "ascii_preview": ascii_preview or None,
        "interpretation": (
            "LSB statistics are indicators only. Equalised bit pairs may also occur naturally, "
            "and encrypted or keyed payloads cannot be reliably identified by this module."
        ),
    }
    return LsbResult(findings=findings, extracted_payload=payload)
