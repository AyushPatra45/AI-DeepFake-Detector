from __future__ import annotations

from pathlib import Path

PROVIDER_MARKERS = {
    b"adobe firefly": "Adobe Firefly",
    b"dall-e": "DALL-E",
    b"gemini": "Google Gemini",
    b"google ai": "Google AI",
    b"google c2pa": "Google C2PA",
    b"google generative ai": "Google Generative AI",
    b"midjourney": "Midjourney",
    b"stable diffusion": "Stable Diffusion",
}

AI_CLAIM_MARKERS = {
    b"added imperceptible synthid watermark": "Added imperceptible SynthID watermark",
    b"algorithmicmedia": "Algorithmic media",
    b"created by google generative ai": "Created by Google Generative AI",
    b"trainedalgorithmicmedia": "Trained algorithmic media",
}


def scan_provenance_markers(path: Path, *, chunk_bytes: int = 8 * 1024 * 1024) -> dict:
    size = path.stat().st_size
    with path.open("rb") as source:
        head = source.read(chunk_bytes)
        tail = b""
        if size > chunk_bytes:
            source.seek(max(0, size - chunk_bytes))
            tail = source.read(chunk_bytes)

    searchable = (head + tail).lower()
    c2pa_markers = [
        marker.decode("ascii")
        for marker in (b"c2pa", b"content credentials", b"jumb")
        if marker in searchable
    ]
    providers = sorted(
        {name for marker, name in PROVIDER_MARKERS.items() if marker in searchable}
    )
    ai_claims = sorted(
        {claim for marker, claim in AI_CLAIM_MARKERS.items() if marker in searchable}
    )
    return {
        "c2pa_marker_detected": bool(c2pa_markers),
        "c2pa_markers": c2pa_markers,
        "ai_origin_claim_detected": bool(ai_claims),
        "ai_origin_claims": ai_claims,
        "signature_verified": False,
        "provider_markers": providers,
        "interpretation": (
            "Claims are extracted as file-level provenance leads. A complete C2PA validator "
            "is still required to verify signatures and claim integrity."
        ),
    }
